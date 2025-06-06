from PIL import Image, ImageDraw
import hashlib
import numpy as np
from scipy.ndimage import label, find_objects
from pillow_heif import register_heif_opener

register_heif_opener()

def open_image(file):
    file.stream.seek(0)
    return Image.open(file.stream).convert("RGB")

def resize_image(image, max_size=1024):
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        print(f"DEBUG: Resizing image from {image.size} to {new_size}")
        return image.resize(new_size, Image.LANCZOS)
    print(f"DEBUG: Image size {image.size} no resize needed")
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
            (min(x_stop + padding, img.width), min(y_stop + padding, img.height)),
        ]
        draw.rectangle(box, outline=(255, 105, 180), width=3)
