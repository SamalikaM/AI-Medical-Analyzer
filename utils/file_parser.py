"""
Uploaded file -> plain text. Tries the embedded text layer first (fast,
exact); falls back to OCR only for pages/files that have none -- covers
scanned or photographed reports, not just typed PDFs.

# ponytail: OCR uses Tesseract's default (printed-text-trained) model.
# Ceiling: clean printed/typed reports OCR reliably; true handwritten
# cursive does not -- Tesseract was never trained for that and accuracy
# on it is low. Upgrade path: a handwriting-specific model (e.g. a cloud
# handwriting API) would slot in here as an additional fallback after
# this OCR pass, same return type, nothing else in the app changes.
"""
import os
import shutil

import fitz  # PyMuPDF, used only to rasterize PDF pages for OCR
import pdfplumber
import pytesseract
from PIL import Image, ImageOps

# ponytail: Windows' Tesseract installer often doesn't add itself to PATH.
# Ceiling: only checks the one default install location. Upgrade path: set
# TESSERACT_CMD in .env if installed elsewhere.
if shutil.which("tesseract") is None:
    _default_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_default_win_path):
        pytesseract.pytesseract.tesseract_cmd = _default_win_path

ALLOWED_EXTENSIONS = {"pdf", "txt", "png", "jpg", "jpeg"}
MIN_TEXT_LEN = 20  # below this, treat a PDF page as "no real text layer" -> OCR it
# uniform block of text (a report) reads more reliably than Tesseract's
# default "assume a full page layout" mode
_TESSERACT_CONFIG = "--psm 6"


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """Grayscale + contrast stretch. Measurably helps OCR on low-contrast
    scans/photos (poor lighting, faint print) in testing, without
    introducing new misreads. Does NOT make handwriting recognition
    reliable -- that's a different, harder problem this can't touch.

    # ponytail: a fixed-threshold binarization step was tried here too and
    # reverted -- it corrupted unit text on a moderately degraded test
    # image instead of helping. Not shipping an "improvement" that isn't
    # actually proven better. Upgrade path: adaptive/Otsu thresholding
    # could be revisited with a larger real-world test set.
    """
    gray = ImageOps.grayscale(img)
    return ImageOps.autocontrast(gray, cutoff=1)


def _ocr_image(img: Image.Image) -> str:
    return pytesseract.image_to_string(_preprocess_for_ocr(img), config=_TESSERACT_CONFIG)


def extract_text(filepath: str) -> str:
    ext = filepath.rsplit(".", 1)[1].lower()

    if ext == "txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    if ext in ("png", "jpg", "jpeg"):
        return _ocr_image(Image.open(filepath))

    if ext == "pdf":
        text_parts = []
        with pdfplumber.open(filepath) as pdf, fitz.open(filepath) as doc:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                if len(page_text.strip()) < MIN_TEXT_LEN:
                    # no usable text layer on this page (scanned/photographed) -> OCR it
                    pix = doc[i].get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    page_text = _ocr_image(img)
                text_parts.append(page_text)
        return "\n".join(text_parts)

    return ""
