from flask import Flask, request, render_template, redirect, url_for, flash, session
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
    if 'original_filename' not in session:
        session['original_filename'] = None
    if 'processed_filename' not in session:
        session['processed_filename'] = None
    if 'key' not in session:
        session['key'] = None

    if request.method == 'POST':
        # Upload original image
        if 'original' in request.files:
            file = request.files['original']
            if file.filename == '':
                flash('No selected file for original image')
                return redirect(request.url)

            original_img = open_image(file)
            filename = 'original_' + file.filename.rsplit('.',1)[0] + '.jpg'
            original_path = os.path.join(UPLOAD_FOLDER, filename)
            original_img.save(original_path, format='JPEG')

            session['original_filename'] = filename
            session['processed_filename'] = None  # reset processed
            session['key'] = file.filename  # key is original filename

            flash('Original image uploaded and key saved')
            return redirect(url_for('index'))

        # Upload suspect image
        if 'suspect' in request.files:
            if session.get('original_filename') is None or session.get('key') is None:
                flash('Please upload original image first')
                return redirect(request.url)

            file = request.files['suspect']
            if file.filename == '':
                flash('No selected file for suspect image')
                return redirect(request.url)

            suspect_img = open_image(file)
            original_img = Image.open(os.path.join(UPLOAD_FOLDER, session['original_filename'])).convert('RGB')

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
            draw_green_dot(suspect_marked, session['key'])

            processed_filename = 'processed_' + file.filename.rsplit('.',1)[0] + '.jpg'
            processed_path = os.path.join(UPLOAD_FOLDER, processed_filename)
            suspect_marked.save(processed_path, format='JPEG')

            session['processed_filename'] = processed_filename

            flash('Tampering detected! See result below.')
            return redirect(url_for('index'))

    return render_template(
        'index.html',
        original_img=session.get('original_filename'),
        processed_img=session.get('processed_filename')
    )


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
