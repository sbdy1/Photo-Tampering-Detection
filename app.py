from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from PIL import Image, ImageDraw
import hashlib
import numpy as np
from scipy.ndimage import label, find_objects
import os
import io
import pyheif

app = Flask(__name__)
app.secret_key = 'replace_with_your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024  # Limit uploads to 60MB

def open_image(file):
    filename = file.filename.lower()
    if filename.endswith('.heic') or filename.endswith('.heif'):
        heif_file = pyheif.read(file.stream.read())
        image = Image.frombytes(
            heif_file.mode, 
            heif_file.size, 
            heif_file.data, 
            "raw", 
            heif_file.mode, 
            heif_file.stride
        )
        return image.convert('RGB')
    else:
        file.stream.seek(0)
        return Image.open(file.stream).convert('RGB')

def resize_image(image, max_size=1024):
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        return image.resize(new_size, Image.LANCZOS)
    return image

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
            (min(x_stop + padding, img.width), min(y_stop + padding, img.height))
        ]
        draw.rectangle(box, outline=(255, 105, 180), width=3)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_original', methods=['POST'])
def upload_original():
    if 'original' not in request.files or request.files['original'].filename == '':
        return jsonify({'error': 'No original image uploaded'}), 400

    file = request.files['original']
    original_img = resize_image(open_image(file))
    filename = 'original_' + file.filename.rsplit('.', 1)[0] + '.jpg'
    original_path = os.path.join(UPLOAD_FOLDER, filename)
    original_img.save(original_path, format='JPEG')

    session['original_filename'] = filename
    session['key'] = file.filename

    return jsonify({'message': 'Original image uploaded', 'filename': filename})

@app.route('/upload_suspects', methods=['POST'])
def upload_suspects():
    if 'original_filename' not in session or not session['original_filename']:
        return jsonify({'error': 'No original image uploaded'}), 400

    original_path = os.path.join(UPLOAD_FOLDER, session['original_filename'])
    original_img = Image.open(original_path).convert('RGB')

    results = []
    files = request.files.getlist('suspects[]')

    for file in files:
        suspect_img = resize_image(open_image(file))
        if suspect_img.size != original_img.size:
            suspect_img = suspect_img.resize(original_img.size)

        orig_np = np.array(original_img)
        suspect_np = np.array(suspect_img)
        diff = np.abs(orig_np.astype(int) - suspect_np.astype(int)).sum(axis=2)

        threshold = 50
        tampered = np.max(diff) > threshold

        processed_img = suspect_img.copy()
        if tampered:
            draw_cluster_boxes(processed_img, diff, threshold)
            draw_green_dot(processed_img, session['key'])

        output_name = 'processed_' + file.filename.rsplit('.', 1)[0] + '.jpg'
        processed_path = os.path.join(UPLOAD_FOLDER, output_name)
        processed_img.save(processed_path, format='JPEG')

        results.append({
            'filename': output_name,
            'tampered': tampered,
            'url': url_for('static', filename='uploads/' + output_name)
        })

    return jsonify(results)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
