from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from PIL import Image, ImageChops, ImageEnhance, ExifTags
import pillow_heif
import io
import numpy as np
import cv2
import json

pillow_heif.register_heif_opener()

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def convert_heic_to_jpeg(image_path):
    try:
        img = Image.open(image_path)
        if img.format in ["HEIC", "HEIF"]:
            output_buffer = io.BytesIO()
            img.save(output_buffer, format="JPEG", quality=95)
            output_buffer.seek(0)
            return Image.open(output_buffer)
        return img
    except Exception as e:
        print(f"Error converting HEIC: {e}")
        return None

def ela_analysis(image_path, output_folder):
    try:
        original_image = Image.open(image_path).convert("RGB")
        temp_path = os.path.join(output_folder, "temp_ela.jpg")
        original_image.save(temp_path, quality=app.config["ELA_QUALITY"])

        recompressed_image = Image.open(temp_path)

        diff = ImageChops.difference(original_image, recompressed_image)
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        scale = 255.0 / max_diff if max_diff > 0 else 1
        ela_image = ImageEnhance.Brightness(diff).enhance(scale)

        ela_output_path = os.path.join(output_folder, os.path.basename(image_path).split(".")[0] + "_ela.jpg")
        ela_image.save(ela_output_path)
        os.remove(temp_path) # Clean up temporary file
        return ela_output_path
    except Exception as e:
        print(f"Error during ELA analysis: {e}")
        return None

def noise_analysis(image_path, output_folder):
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return None

        # Simple noise visualization (e.g., high-pass filter)
        kernel = np.array([[-1,-1,-1],
                           [-1, 9,-1],
                           [-1,-1,-1]])
        noise_img = cv2.filter2D(img, -1, kernel)

        noise_output_path = os.path.join(output_folder, os.path.basename(image_path).split(".")[0] + "_noise.jpg")
        cv2.imwrite(noise_output_path, noise_img)
        return noise_output_path
    except Exception as e:
        print(f"Error during Noise Analysis: {e}")
        return None

def copy_move_detection(image_path, output_folder):
    # This is a highly simplified placeholder. Real copy-move detection is complex.
    # For demonstration, we'll just create a red rectangle on a copy of the image.
    try:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        # Draw a red rectangle as a placeholder for detected copy-move area
        draw.rectangle([(50, 50), (150, 150)], outline="red", width=5)

        copy_move_output_path = os.path.join(output_folder, os.path.basename(image_path).split(".")[0] + "_copymove.jpg")
        img.save(copy_move_output_path)
        return copy_move_output_path
    except Exception as e:
        print(f"Error during Copy-Move Detection: {e}")
        return None

def metadata_analysis(image_path):
    try:
        img = Image.open(image_path)
        exif_data = {}
        if hasattr(img, "_getexif") and img._getexif() is not None:
            for tag, value in img._getexif().items():
                decoded = ExifTags.TAGS.get(tag, tag)
                exif_data[decoded] = str(value)
        return exif_data
    except Exception as e:
        print(f"Error during Metadata Analysis: {e}")
        return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    selected_methods = request.form.getlist("methods") # Get selected methods

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        original_filename = file.filename
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], original_filename)
        file.save(filepath)

        img = convert_heic_to_jpeg(filepath)
        if img is None:
             return jsonify({"error": "Could not process image file"}), 500
        
        converted_filepath = os.path.join(app.config["UPLOAD_FOLDER"], "converted_" + original_filename.rsplit(".", 1)[0] + ".jpg")
        img.save(converted_filepath)

        results = {}
        if "ela" in selected_methods or not selected_methods: # Run ELA if selected or no methods specified
            ela_output_path = ela_analysis(converted_filepath, app.config["UPLOAD_FOLDER"])
            if ela_output_path:
                results["ela_result"] = os.path.basename(ela_output_path)

        if "noise" in selected_methods or not selected_methods: # Run Noise if selected or no methods specified
            noise_output_path = noise_analysis(converted_filepath, app.config["UPLOAD_FOLDER"])
            if noise_output_path:
                results["noise_result"] = os.path.basename(noise_output_path)

        if "copymove" in selected_methods or not selected_methods: # Run Copy-Move if selected or no methods specified
            # Need to import ImageDraw for copy_move_detection placeholder
            from PIL import ImageDraw
            copy_move_output_path = copy_move_detection(converted_filepath, app.config["UPLOAD_FOLDER"])
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

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

