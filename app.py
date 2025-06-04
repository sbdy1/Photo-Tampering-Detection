from flask import Flask, request, render_template, redirect, url_for, send_file, flash
from PIL import Image, ImageDraw
import hashlib
import numpy as np
from scipy.ndimage import label, find_objects
import os
import io

app = Flask(__name__)
app.secret_key = 'replace_with_your_secret_key'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

original_path = None
key = None

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

@app.route('/', methods=['GET', 'POST'])
def index():
    global original_path, key

    if request.method == 'POST':
        # Upload original image and save key
        if 'original' in request.files:
            file = request.files['original']
            if file.filename == '':
                flash('No selected file for original image')
                return redirect(request.url)
            filename = 'original_' + file.filename
            original_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(original_path)
            key = file.filename  # key = filename
            flash(f'Original image uploaded and key saved: {key}')
            return redirect(url_for('index'))

        # Upload suspect image for comparison
        if 'suspect' in request.files:
            if original_path is None or key is None:
                flash('Please upload original image first')
                return redirect(request.url)
            file = request.files['suspect']
            if file.filename == '':
                flash('No selected file for suspect image')
                return redirect(request.url)
            suspect_img = Image.open(file.stream).convert('RGB')
            original_img = Image.open(original_path).convert('RGB')

            if suspect_img.size != original_img.size:
                suspect_img = suspect_img.resize(original_img.size)

            orig_np = np.array(original_img)
            suspect_np = np.array(suspect_img)
            diff = np.abs(orig_np.astype(int) - suspect_np.astype(int)).sum(axis=2)

            threshold = 50
            if np.max(diff) <= threshold:
                flash('No tampering detected in this image.')
                return redirect(url_for('index'))

            suspect_marked = suspect_img.copy()
            draw_cluster_boxes(suspect_marked, diff, threshold)
            draw_green_dot(suspect_marked, key)

            # Save output to in-memory file
            img_io = io.BytesIO()
            suspect_marked.save(img_io, 'JPEG')
            img_io.seek(0)
            return send_file(img_io, mimetype='image/jpeg')

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
