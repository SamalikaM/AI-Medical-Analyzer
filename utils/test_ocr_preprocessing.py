"""
Runnable self-check for OCR preprocessing (utils/file_parser.py's
_preprocess_for_ocr). Requires Tesseract to be installed and on PATH (or at
the default Windows location) -- kept separate from test_core_logic.py so
that check keeps working with zero external dependencies for anyone who
hasn't installed Tesseract yet.

Usage: python utils/test_ocr_preprocessing.py   (run from project root)
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytesseract
from PIL import Image, ImageDraw, ImageFont

from utils.file_parser import _preprocess_for_ocr, _TESSERACT_CONFIG


def _make_test_image(fill_color, bg_color, blur=0.0):
    from PIL import ImageFilter
    img = Image.new("RGB", (700, 100), bg_color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 30), "Hemoglobin 10.8 g/dL 12.0-16.5", font=font, fill=fill_color)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return img


def main():
    if not _tesseract_available():
        print("SKIPPED: Tesseract isn't installed/found -- nothing to check here yet.")
        return

    # a clean, high-contrast image should read perfectly either way
    clean = _make_test_image((0, 0, 0), (255, 255, 255))
    raw_text = pytesseract.image_to_string(clean, config=_TESSERACT_CONFIG)
    assert "Hemoglobin" in raw_text and "10.8" in raw_text, f"clean image failed to OCR: {raw_text!r}"

    # a low-contrast, slightly blurred image should still read correctly
    # after preprocessing (this is the actual case preprocessing targets)
    degraded = _make_test_image((110, 105, 98), (195, 192, 185), blur=0.7)
    processed_text = pytesseract.image_to_string(_preprocess_for_ocr(degraded), config=_TESSERACT_CONFIG)
    assert "Hemoglobin" in processed_text and "10.8" in processed_text, (
        f"preprocessing did not recover a readable result on a degraded image: {processed_text!r}"
    )

    print("All OCR preprocessing checks passed.")


def _tesseract_available():
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    main()
