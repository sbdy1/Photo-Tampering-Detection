from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw
import hashlib
import numpy as np
from scipy.ndimage import label, find_objects
import os
import pyheif

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key")

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'heic'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024  # 60MB


# ---------- Utility Functions ----------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def open_image(file):
    filename = file.filename.lower()
    if filename.endswith(('.heic', '.heif')):
        heif_file = pyheif.read(file.stream.read())
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
        return image.convert("RGB")
    else:
        file.stream.seek(0)
        return Image.open(file.stream).convert("RGB")

def resize_image(image, max_size=1024):
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        return image.resize(new_size, Image.LANCZOS)
    return image

def compress_and_save(image, path, quality=85):
    image.save(path, format="JPEG", quality=quality, optimize=True)

def get_signature_position(img_size, key):
    width, height = img_size
    hashed = hashlib.sha256(key.encode()).hexdigest()
    x = int(hashed[:8], 16) % width
    y = int(hashed[8:16], 16) % height
    return x, y

def draw_green_dot(img, key):
    draw = ImageDraw.Draw(img)
    x, y = get_signature_position(img.size, key)
    radius = 10
    box = [(x - radius, y - radius), (x + radius, y + radius)]
    draw.ellipse(box, fill=(0, 255, 0))

def draw_cluster_boxes(img, diff, threshold):
    draw = ImageDraw.Draw(img)
    mask = diff > threshold
    labeled_array, num_features = label(mask)
    regions = find_objects(labeled_array)
    for region in regions:
        y_start, y_stop = region[0].start, region[0].stop
        x_start, x_stop = region[1].start, region[1].stop
        padding = 3
        box = [
            (max(x_start - padding, 0), max(y_start - padding, 0)),
            (min(x_stop + padding, img.width), min(y_stop + padding, img.height)),
        ]
        draw.rectangle(box, outline=(255, 105, 180), width=3)


# ---------- Routes ----------

@app.route("/", methods=["GET"])
def index():
    original_filename = session.get("original_filename")
    processed_filenames = session.get("processed_filenames", [])
    print("Session original_filename:", original_filename)  # check server console
    return render_template("index.html",
                           original_filename=original_filename,
                           processed_filenames=processed_filenames)


@app.route("/upload_original", methods=["POST"])
def upload_original():
    print("Session data:", dict(session))
    file = request.files.get("original")
    if not file or file.filename == "" or not allowed_file(file.filename):
        flash("Invalid or missing original image")
        return redirect(url_for("index"))

    key = secure_filename(os.path.splitext(file.filename)[0])
    original_img = resize_image(open_image(file))
    draw_green_dot(original_img, key)

    filename = f"original_{key}.jpg"
    path = os.path.join(UPLOAD_FOLDER, filename)
    compress_and_save(original_img, path)

    session["original_filename"] = filename
    session["key"] = key
    session["processed_filenames"] = []

    flash("Original image uploaded successfully.")
    return redirect(url_for("index"))


@app.route("/upload_suspects", methods=["POST"])
def upload_suspects():
    files = request.files.getlist("suspects")
    if not files:
        flash("No suspect images uploaded")
        return redirect(url_for("index"))

    key = session.get("key")
    original_filename = session.get("original_filename")
    if not key or not original_filename:
        flash("Original image missing")
        return redirect(url_for("index"))

    original_path = os.path.join(UPLOAD_FOLDER, original_filename)
    original_img = Image.open(original_path).convert("RGB")
    processed_filenames = []

    for file in files:
        if not allowed_file(file.filename):
            continue
        safe_name = secure_filename(os.path.splitext(file.filename)[0])
        suspect_img = resize_image(open_image(file))

        if suspect_img.size != original_img.size:
            suspect_img = suspect_img.resize(original_img.size)

        diff = np.abs(np.array(original_img).astype(int) - np.array(suspect_img).astype(int)).sum(axis=2)
        if np.max(diff) <= 50:
            continue

        suspect_marked = suspect_img.copy()
        draw_cluster_boxes(suspect_marked, diff, 50)
        draw_green_dot(suspect_marked, key)

        filename = f"processed_{safe_name}.jpg"
        path = os.path.join(UPLOAD_FOLDER, filename)
        compress_and_save(suspect_marked, path)

        processed_filenames.append(filename)

    session["processed_filenames"] = processed_filenames

    flash(f"Processed {len(processed_filenames)} suspect images.")
    print("Session data:", dict(session))
    return redirect(url_for("index"))


@app.route("/clear", methods=["POST"])
def clear():
    session.clear()
    flash("Session cleared.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
