from flask import Blueprint, request, redirect, url_for, flash, session, current_app, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image, ImageChops, ImageEnhance, ExifTags, ImageDraw
import os
import numpy as np
from .utils import (
    open_image, resize_image, draw_green_dot, draw_cluster_boxes,
    allowed_file, convert_heic_to_jpeg, ela_analysis, noise_analysis,
    copy_move_detection, metadata_analysis
)
import pillow_heif
import io
import cv2
import json
import traceback

pillow_heif.register_heif_opener()

bp = Blueprint("upload", __name__)

MAX_IMAGE_SIZE_MB = 10
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

def resize_image_file(img, max_bytes=MAX_IMAGE_SIZE_BYTES):
    """
    Compress image to be under max_bytes by reducing quality.
    """
    buffer = io.BytesIO()
    quality = 95
    img.save(buffer, format="JPEG", quality=quality)
    size = buffer.tell()

    while size > max_bytes and quality > 20:
        buffer = io.BytesIO()
        quality -= 5
        img.save(buffer, format="JPEG", quality=quality)
        size = buffer.tell()

    buffer.seek(0)
    return Image.open(buffer)

def resize_image_dimensions(img, max_pixels=1920):
    """
    Resize image dimensions to a max width or height of max_pixels.
    """
    width, height = img.size
    if max(width, height) <= max_pixels:
        return img

    ratio = max_pixels / float(max(width, height))
    new_size = (int(width * ratio), int(height * ratio))
    return img.resize(new_size, Image.ANTIALIAS)

@bp.route("/upload_original", methods=["POST"])
def upload_original():
    if "original" not in request.files:
        flash("No original image file part.")
        return redirect(url_for("main.index"))

    file = request.files["original"]
    if file.filename == "":
        flash("No selected file for original image")
        return redirect(url_for("main.index"))

    safe_name = secure_filename(os.path.splitext(file.filename)[0])
    original_filename = f"original_{safe_name}.jpg"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    original_path = os.path.join(upload_folder, original_filename)

    original_img = resize_image(open_image(file))
    draw_green_dot(original_img, safe_name)

    try:
        original_img.save(original_path, format="JPEG")
        print(f"DEBUG: Image saved successfully at {original_path}")
    except Exception as e:
        print(f"ERROR: Failed to save image: {e}")
        flash("Failed to save image on server.")
        return redirect(url_for("main.index"))

    session["original_filename"] = original_filename
    session["key"] = safe_name
    session["processed_filenames"] = []

    flash("Original image uploaded and green signature added.")
    return redirect(url_for("main.index"))

@bp.route("/upload_suspects", methods=["POST"])
def upload_suspects():
    if "suspects" not in request.files:
        flash("No suspect images file part.")
        return redirect(url_for("main.index"))

    if session.get("original_filename") is None or session.get("key") is None:
        flash("Please upload the original image first.")
        return redirect(url_for("main.index"))

    files = request.files.getlist("suspects")
    if not files or all(f.filename == "" for f in files):
        flash("No selected files for suspect images")
        return redirect(url_for("main.index"))

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    original_filename = session["original_filename"]
    original_path = os.path.join(upload_folder, original_filename)

    if not os.path.exists(original_path):
        flash("Original image file not found. Please re-upload.")
        return redirect(url_for("main.index"))

    original_img = Image.open(original_path).convert("RGB")
    processed_filenames = []

    for file in files:
        safe_name = secure_filename(os.path.splitext(file.filename)[0])
        suspect_img = resize_image(open_image(file))

        if suspect_img.size != original_img.size:
            suspect_img = suspect_img.resize(original_img.size)

        orig_np = np.array(original_img)
        suspect_np = np.array(suspect_img)
        diff = np.abs(orig_np.astype(int) - suspect_np.astype(int)).sum(axis=2)

        threshold = 50
        if np.max(diff) <= threshold:
            flash(f"No tampering detected in image: {file.filename}")
            continue

        suspect_marked = suspect_img.copy()
        draw_cluster_boxes(suspect_marked, diff, threshold)
        draw_green_dot(suspect_marked, session["key"])

        processed_filename = f"processed_{safe_name}.jpg"
        processed_path = os.path.join(upload_folder, processed_filename)

        try:
            suspect_marked.save(processed_path, format="JPEG")
        except Exception as e:
            print(f"ERROR: Failed to save suspect image: {e}")
            flash(f"Could not save processed image: {file.filename}")
            continue

        processed_filenames.append(processed_filename)

    session["processed_filenames"] = processed_filenames

    if processed_filenames:
        flash("Tampering detected! See results below.")
    else:
        flash("No tampering detected in any suspect images.")

    return redirect(url_for("main.index"))

@bp.route("/enhanced_detection")
def enhanced_detection_page():
    return render_template("enhanced_detection.html")

@bp.route("/analyze_enhanced", methods=["POST"])
def analyze_enhanced_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    selected_methods = request.form.getlist("methods") # Get selected methods

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        original_filename = secure_filename(file.filename)
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        filepath = os.path.join(upload_folder, original_filename)
        file.save(filepath)

        img = convert_heic_to_jpeg(filepath)
        if img is None:
             return jsonify({"error": "Could not process image file"}), 500
        
        converted_filepath = os.path.join(upload_folder, "converted_" + original_filename.rsplit(".", 1)[0] + ".jpg")
        img.save(converted_filepath)

        results = {}
        if "ela" in selected_methods or not selected_methods: # Run ELA if selected or no methods specified
            ela_output_path = ela_analysis(converted_filepath, upload_folder, current_app.config["ELA_QUALITY"])
            if ela_output_path:
                results["ela_result"] = os.path.basename(ela_output_path)

        if "noise" in selected_methods or not selected_methods: # Run Noise if selected or no methods specified
            noise_output_path = noise_analysis(converted_filepath, upload_folder)
            if noise_output_path:
                results["noise_result"] = os.path.basename(noise_output_path)

        if "copymove" in selected_methods or not selected_methods: # Run Copy-Move if selected or no methods specified
            copy_move_output_path = copy_move_detection(converted_filepath, upload_folder)
            if copy_move_output_path:
                results["copy_move_result"] = os.path.basename(copy_move_output_path)

        if "metadata" in selected_methods or not selected_methods: # Run Metadata if selected or no methods specified
            metadata = metadata_analysis(converted_filepath)
            if metadata:
                results["metadata_result"] = metadata

        if converted_filepath != filepath:
            os.remove(converted_filepath)

        return jsonify({"message": "Analysis complete", "results": results})

    else:
        return jsonify({"error": "File type not allowed"}), 400

@bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
