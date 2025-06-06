from flask import Blueprint, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from PIL import Image
import os
import numpy as np
from .utils import open_image, resize_image, draw_green_dot, draw_cluster_boxes

bp = Blueprint("upload", __name__)

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
