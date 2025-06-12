import os
from PIL import Image, ImageChops, ImageEnhance, ExifTags, ImageDraw
from PIL.ExifTags import TAGS
import pillow_heif
import io
import numpy as np
import cv2
import pyheif
import piexif

pillow_heif.register_heif_opener()

def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

def convert_heic_to_jpeg(image_path):
    try:
        # Check if the file is actually HEIC/HEIF before trying pyheif
        # Read a small portion of the file to check for HEIC/HEIF signatures
        with open(image_path, 'rb') as f:
            header = f.read(12)
            if not (b'ftypheic' in header or b'ftypheif' in header or b'ftypmif1' in header):
                # Not a HEIC/HEIF file, open directly with PIL
                img = Image.open(image_path)
                return img

        heif_file = pyheif.read(image_path)

        # Extract metadata if available
        exif_data = None
        for metadata in heif_file.metadata or []:
            if metadata['type'] == 'Exif':
                exif_data = metadata['data']

        image = Image.frombytes(
            heif_file.mode, heif_file.size, heif_file.data,
            "raw", heif_file.mode
        )

        output_buffer = io.BytesIO()
        if exif_data:
            # piexif.insert takes bytes, not a path
            # Need to load the exif data using piexif.load first if it's raw bytes
            try:
                exif_dict = piexif.load(exif_data)
                exif_bytes = piexif.dump(exif_dict)
            except Exception as e:
                print(f"Error loading/dumping EXIF data: {e}")
                exif_bytes = b'' # Fallback to no exif if error
            image.save(output_buffer, format="JPEG", quality=95, exif=exif_bytes)
        else:
            image.save(output_buffer, format="JPEG", quality=95)
        output_buffer.seek(0)
        return Image.open(output_buffer)

    except Exception as e:
        print(f"Error converting HEIC: {e}")
        return None

def ela_analysis(image_path, output_folder, quality=90):
    try:
        original_image = Image.open(image_path).convert("RGB")
        temp_path = os.path.join(output_folder, "temp_ela.jpg")
        original_image.save(temp_path, quality=quality)

        recompressed_image = Image.open(temp_path)

        diff = ImageChops.difference(original_image, recompressed_image)
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        scale = 255.0 / max_diff if max_diff > 0 else 1
        ela_image = ImageEnhance.Brightness(diff).enhance(scale)

        ela_output_path = os.path.join(output_folder, os.path.basename(image_path).split(".")[0] + "_ela.jpg")
        ela_image.save(ela_output_path)
        os.remove(temp_path)
        return ela_output_path
    except Exception as e:
        print(f"Error during ELA analysis: {e}")
        return None

def noise_analysis(image_path, output_folder):
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return None

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
    try:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.rectangle([(50, 50), (150, 150)], outline="red", width=5)

        output_path = os.path.join(output_folder, os.path.basename(image_path).split(".")[0] + "_copymove.jpg")
        img.save(output_path)
        return output_path
    except Exception as e:
        print(f"Error during Copy-Move Detection: {e}")
        return None
        
def metadata_analysis(image_path):
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()

        if not exif_data:
            return {"Info": "No metadata found (Image may lack EXIF)"}

        metadata = {}
        for tag, value in exif_data.items():
            decoded = TAGS.get(tag, tag)
            metadata[decoded] = str(value) # Convert value to string to avoid JSON serialization issues

        return metadata

    except Exception as e:
        print(f"Error during Metadata Analysis: {e}")
        return {"Error": str(e)}
