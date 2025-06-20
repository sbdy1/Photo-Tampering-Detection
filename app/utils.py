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
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def convert_heic_to_jpeg(image_path):
    try:
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
            image.save(output_buffer, format="JPEG", quality=95, exif=exif_data)
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

        if max_diff > 30:
            result = f"ELA detected high recompression artifacts (max diff: {max_diff}) – possible tampering."
        else:
            result = f"ELA showed minimal differences (max diff: {max_diff}) – likely untampered."

        return ela_output_path, result
    except Exception as e:
        print(f"Error during ELA analysis: {e}")
        return None, f"ELA analysis failed: {str(e)}"

def noise_analysis(image_path, output_folder):
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: 
            return None, "Noise analysis failed – image couldn't be loaded."

        kernel = np.array([[-1,-1,-1],
                           [-1, 9,-1],
                           [-1,-1,-1]])
        noise_img = cv2.filter2D(img, -1, kernel)

        noise_output_path = os.path.join(output_folder, os.path.basename(image_path).split(".")[0] + "_noise.jpg")
        cv2.imwrite(noise_output_path, noise_img)
        
        variance = np.var(noise_img)
        if variance > 1000:
            result = f"High noise variance detected ({variance:.2f}) – may indicate tampering or poor compression."
        else:
            result = f"Low noise variance ({variance:.2f}) – likely consistent with natural image."

        return noise_output_path, result
    except Exception as e:
        return None, f"Noise analysis error: {str(e)}"

def copy_move_detection(image_path, output_folder):
    try:
        # Load image using OpenCV
        img_cv = cv2.imread(image_path)
        if img_cv is None:
            return None, "Copy-move detection failed – image couldn't be loaded."

        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # ORB feature detector
        orb = cv2.ORB_create(nfeatures=1000)
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        if descriptors is None or len(keypoints) < 2:
            return None, "Not enough keypoints for copy-move detection."

        # BFMatcher with Hamming distance
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(descriptors, descriptors)

        # Filter matches (remove identical keypoints)
        matches = [m for m in matches if m.distance > 0 and abs(m.queryIdx - m.trainIdx) > 10]

        # Draw matches on image
        img_matches = cv2.drawMatches(
            img_cv, keypoints,
            img_cv, keypoints,
            matches[:20], None, flags=2
        )

        output_path = os.path.join(
            output_folder,
            os.path.basename(image_path).split(".")[0] + "_copy_move.jpg"
        )
        cv2.imwrite(output_path, img_matches)

        result_text = f"Copy-move detection completed – {len(matches)} matches found (displaying top 20)."
        return output_path, result_text

    except Exception as e:
        return None, f"Copy-Move detection error: {str(e)}"
        
def metadata_analysis(image_path):
    try:
        img = Image.open(image_path)
        print(f"[DEBUG] Format: {img.format}, Info keys: {img.info.keys()}")
        exif_data = img._getexif()
        print(f"[DEBUG] EXIF raw: {exif_data}")

        if not exif_data:
            if img.format in ["HEIC", "HEIF"]:
                return {"Info": "No metadata found (HEIC format not fully supported for EXIF)"}
            return {"Info": "No metadata found (Image may lack EXIF)"}

        metadata = {}
        for tag, value in exif_data.items():
            decoded = TAGS.get(tag, tag)
            metadata[decoded] = value

        return metadata

    except Exception as e:
        return {"Error": str(e)}
