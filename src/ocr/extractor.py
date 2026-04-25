import os
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image, ImageOps
import pytesseract

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Configuração Tesseract: psm 6 = bloco uniforme de texto (bom para provas)
TESSERACT_CONFIG = "--psm 6"
# Dimensão máxima após redimensionamento (mantém qualidade do OCR sem ser lento)
MAX_OCR_DIM = 2400


def _preprocess_image(img: Image.Image) -> Image.Image:
    """Pré-processa imagem para melhorar OCR e reduzir tempo:
    - Redimensiona se maior que MAX_OCR_DIM (mantém proporção)
    - Converte para escala de cinza
    - Aplica auto-contraste (compensa iluminação irregular de fotos de celular)
    """
    # Aplica orientação EXIF (fotos de celular geralmente vêm rotacionadas)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Redimensiona se for muito grande
    largest = max(img.size)
    if largest > MAX_OCR_DIM:
        ratio = MAX_OCR_DIM / largest
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Converte para escala de cinza (mais rápido + melhor para texto)
    if img.mode != "L":
        img = img.convert("L")

    # Auto-contraste compensa fotos com sombra/iluminação ruim
    img = ImageOps.autocontrast(img, cutoff=2)

    return img


def _extract_direct(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    return text


def _extract_ocr_pdf(pdf_path: str, on_progress: Optional[Callable] = None) -> str:
    text = ""
    doc = fitz.open(pdf_path)
    total = len(doc)

    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, page in enumerate(doc):
            if on_progress:
                on_progress(0.1 + 0.7 * (i / total), f"OCR: página {i + 1}/{total}...")
            # 200 DPI é suficiente para texto e mais rápido que 300
            mat = fitz.Matrix(200 / 72, 200 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_path = os.path.join(tmp_dir, f"p{i}.png")
            pix.save(img_path)
            img = Image.open(img_path)
            img = _preprocess_image(img)
            text += pytesseract.image_to_string(img, lang="por", config=TESSERACT_CONFIG) + "\n"

    doc.close()
    return text


def _extract_ocr_image(image_path: str) -> str:
    img = Image.open(image_path)
    img = _preprocess_image(img)
    return pytesseract.image_to_string(img, lang="por", config=TESSERACT_CONFIG)


def _is_scanned(pdf_path: str) -> bool:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            sample = pdf.pages[: min(3, len(pdf.pages))]
            texts = [(p.extract_text() or "").strip() for p in sample]
            if not any(texts):
                return True
            if len(set(texts)) == 1 and len(texts[0]) < 200:
                return True
            if sum(len(t) for t in texts) < 150:
                return True
        return False
    except Exception:
        return True


def extract_text_from_file(
    file_path: str,
    on_progress: Optional[Callable] = None,
) -> Tuple[str, str]:
    """
    Extract text from PDF or image file.
    Returns (extracted_text, method) where method is 'direct' or 'ocr'.
    """
    ext = Path(file_path).suffix.lower()

    if ext in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"):
        if on_progress:
            on_progress(0.3, "Processando imagem com OCR...")
        text = _extract_ocr_image(file_path)
        return text, "ocr"

    if ext == ".pdf":
        if on_progress:
            on_progress(0.1, "Analisando PDF...")
        if _is_scanned(file_path):
            text = _extract_ocr_pdf(file_path, on_progress)
            return text, "ocr"
        else:
            if on_progress:
                on_progress(0.5, "Extraindo texto do PDF...")
            text = _extract_direct(file_path)
            return text, "direct"

    raise ValueError(f"Formato não suportado: {ext}")
