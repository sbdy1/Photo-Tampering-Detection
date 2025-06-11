from flask import Blueprint, request, jsonify, current_app, render_template, send_from_directory
from werkzeug.utils import secure_filename
import os
import io
from .utils import (
    allowed_file,
    convert_heic_to_jpeg,
    ela_analysis,
    noise_analysis,
    copy_move_detection,
    metadata_analysis,
)
from PIL import Image

bp = Blueprint("upload", __name__)

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/analyze", methods=["POST"])
def analyze_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    selected_methods = request.form.getlist("methods")
    app = current_app

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename, app.config["ALLOWED_EXTENSIONS"]):
        original_filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], original_filename)
        file.save(filepath)

        img = convert_heic_to_jpeg(filepath)
        if img is None:
            return jsonify({"error": "Could not process image file"}), 500

        converted_filename = "converted_" + original_filename.rsplit(".", 1)[0] + ".jpg"
        converted_filepath = os.path.join(app.config["UPLOAD_FOLDER"], converted_filename)
        img.save(converted_filepath)

        results = {}

        if "ela" in selected_methods or not selected_methods:
            ela_output = ela_analysis(converted_filepath, app.config["UPLOAD_FOLDER"], app.config["ELA_QUALITY"])
            if ela_output:
                results["ela_result"] = os.path.basename(ela_output)

        if "noise" in selected_methods or not selected_methods:
            noise_output = noise_analysis(converted_filepath, app.config["UPLOAD_FOLDER"])
            if noise_output:
                results["noise_result"] = os.path.basename(noise_output)

        if "copymove" in selected_methods or not selected_methods:
            copymove_output = copy_move_detection(converted_filepath, app.config["UPLOAD_FOLDER"])
            if copymove_output:
                results["copy_move_result"] = os.path.basename(copymove_output)

        if "metadata" in selected_methods or not selected_methods:
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
