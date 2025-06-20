from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
import os, traceback
import io
from PIL import Image, ImageOps
from .utils import (
    allowed_file,
    convert_heic_to_jpeg,
    ela_analysis,
    noise_analysis,
    copy_move_detection,
    metadata_analysis,
)

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
    return img.resize(new_size, Image.Resampling.LANCZOS)

@bp.route("/analyze", methods=["POST"])
def analyze_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    methods = request.form.getlist('methods')
    # Accept methods as comma-separated string or multiple form fields
    raw_methods = request.form.get("methods") or ""
    selected_methods = request.form.getlist("methods") or raw_methods.split(",")
    selected_methods = [method.strip().lower() for method in selected_methods if method.strip()]
    print("Selected methods:", selected_methods)

    app = current_app

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename, app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"error": "File type not allowed"}), 400

    # Save uploaded file
    original_filename = secure_filename(file.filename)
    original_filepath = os.path.join(app.config["UPLOAD_FOLDER"], original_filename)
    file.save(original_filepath)
    print("Saved uploaded file:", original_filepath)

    # Initialize img to avoid 'referenced before assignment' error
    img = None
    try:
        if file.filename.lower().endswith(".heic"):
            img = convert_heic_to_jpeg(original_filepath)
        else:
            img = Image.open(original_filepath)
    except Exception as e:
        print("[ERROR] Could not open image:", e)
        traceback.print_exc()
        return jsonify({"error": f"Could not open image: {str(e)}"}), 500

    if img is None:
        return jsonify({"error": "Could not process image file"}), 500

    # Resize/compress
    img = resize_image_dimensions(img)
    img = resize_image_file(img)

    try:
        print("Image mode:", img.mode)
        print("Image format:", img.format)
        print("Image size:", img.size)

        if img.mode not in ["RGB", "RGBA"]:
            print("Converting image mode from", img.mode, "to RGB")
            img = img.convert("RGB")

        converted_filename = "converted_" + original_filename.rsplit(".", 1)[0] + ".jpg"
        converted_filepath = os.path.join(app.config["UPLOAD_FOLDER"], converted_filename)

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

        img.save(converted_filepath, format="JPEG")
        print("Converted image saved to:", converted_filepath)
    except Exception as e:
        print("[ERROR] Failed to save converted image:", e)
        return jsonify({"error": f"Could not save converted image: {str(e)}"}), 500

    results = {}

    try:
        print("Starting ELA analysis...")
        if "ela" in selected_methods or not selected_methods:
            ela_output_path, ela_result_text = ela_analysis(converted_filepath, app.config["UPLOAD_FOLDER"], app.config["ELA_QUALITY"])
            print("ELA output:", ela_output_path, ela_result_text)
            if ela_output_path:
                results["ela_image"] = os.path.basename(ela_output_path)
            results["ela_result"] = ela_result_text

        print("Starting Noise analysis...")
        if "noise" in selected_methods or not selected_methods:
            noise_output_path, noise_result_text = noise_analysis(converted_filepath, app.config["UPLOAD_FOLDER"])
            print("Noise output:", noise_output_path, noise_result_text)
            if noise_output_path:
                results["noise_image"] = os.path.basename(noise_output_path)
            results["noise_result"] = noise_result_text

        print("Starting Copy-Move detection...")
        if "copy_move" in selected_methods or not selected_methods:
            print("Running Copy-Move detection...")
            copy_move_output_path, copy_move_result_text = copy_move_detection(converted_filepath, app.config["UPLOAD_FOLDER"])
            print("Copy-Move detection result:", copy_move_result_text)
            print("Copy-Move image path:", copy_move_output_path)
            results["copy_move_result"] = copy_move_result_text
            if copy_move_output_path:
                results["copy_move_image"] = os.path.basename(copy_move_output_path)

        print("Starting Metadata analysis...")
        if "metadata" in selected_methods or not selected_methods:
            metadata = metadata_analysis(converted_filepath)
            print("Metadata output:", metadata)
            results["metadata_result"] = metadata

    except Exception as e:
        print("=== ERROR DURING ANALYSIS ===")
        traceback.print_exc()
        print("=============================")
        return jsonify({"error": "An error occurred during analysis", "details": str(e)}), 500

    # Clean up converted file if different from original
    if converted_filepath != original_filepath:
        try:
            os.remove(converted_filepath)
            print("Deleted temporary file:", converted_filepath)
        except Exception as e:
            print("Error deleting temp file:", e)

    return jsonify({"message": "Analysis complete", "results": results})


@bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
