from flask import Blueprint, request, jsonify, current_app, render_template, send_from_directory
from werkzeug.utils import secure_filename
import os
from .utils import (
    allowed_file,
    convert_heic_to_jpeg,
    ela_analysis,
    noise_analysis,
    copy_move_detection,
    metadata_analysis,
)

bp = Blueprint("upload", __name__)

@bp.route("/analyze", methods=["POST"])
def analyze_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    
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

    # Convert to JPEG if needed
    img = convert_heic_to_jpeg(original_filepath)
    if img is None:
        return jsonify({"error": "Could not process image file"}), 500

    converted_filename = "converted_" + original_filename.rsplit(".", 1)[0] + ".jpg"
    converted_filepath = os.path.join(app.config["UPLOAD_FOLDER"], converted_filename)
    try:
        if img.mode not in ["RGB", "RGBA"]:
            print("Converting image mode from", img.mode, "to RGB")
            img = img.convert("RGB")
        img.save(converted_filepath, format="JPEG")
        print("Converted image saved to:", converted_filepath)
    except Exception as e:
        print("[ERROR] Failed to save converted image:", e)
        return jsonify({"error": f"Could not save converted image: {str(e)}"}), 500

    results = {}

    try:
        if "ela" in selected_methods or not selected_methods:
            ela_output = ela_analysis(converted_filepath, app.config["UPLOAD_FOLDER"], app.config["ELA_QUALITY"])
            print("ELA output:", ela_output)
            if ela_output:
                results["ela_result"] = os.path.basename(ela_output)

        if "noise" in selected_methods or not selected_methods:
            noise_output = noise_analysis(converted_filepath, app.config["UPLOAD_FOLDER"])
            print("Noise output:", noise_output)
            if noise_output:
                results["noise_result"] = os.path.basename(noise_output)

        if "copymove" in selected_methods or not selected_methods:
            copymove_output = copy_move_detection(converted_filepath, app.config["UPLOAD_FOLDER"])
            print("Copy-move output:", copymove_output)
            if copymove_output:
                results["copy_move_result"] = os.path.basename(copymove_output)

        if "metadata" in selected_methods or not selected_methods:
            metadata = metadata_analysis(converted_filepath)
            print("Metadata output:", metadata)
            if metadata:
                results["metadata_result"] = metadata

    except Exception as e:
        print("Analysis error:", e)
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
