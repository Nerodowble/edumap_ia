"""
Extração de texto de PDFs e imagens (OCR).

Pipeline de pré-processamento avançado para fotos de celular:
  1. Aplica orientação EXIF (corrige rotação automática)
  2. Redimensiona para no máximo MAX_OCR_DIM (mantém proporção)
  3. Converte para escala de cinza
  4. Deskew — detecta inclinação do texto e endireita
  5. Denoise — remove ruído de câmera
  6. Binarização Otsu — preto/branco com threshold ótimo
  7. Tesseract com config psm 6 (bloco uniforme de texto)

cv2 (OpenCV) é opcional. Se não estiver instalado, faz fallback para PIL puro.
"""
import os
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image, ImageOps
import pytesseract

try:
    import cv2
    import numpy as np
    _CV2 = True
except ImportError:
    _CV2 = False

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

TESSERACT_CONFIG = "--oem 1 --psm 6"
MAX_OCR_DIM = 2400


def _deskew(gray_array):
    """Detecta inclinação do texto via minAreaRect e corrige."""
    if not _CV2:
        return gray_array
    try:
        # Threshold inverso para destacar pixels de texto (escuros)
        _, thresh = cv2.threshold(
            gray_array, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return gray_array

        angle = cv2.minAreaRect(coords)[-1]
        # Normaliza ângulo: minAreaRect retorna em [-90, 0]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Ignora correções muito pequenas (provavelmente ruído)
        if abs(angle) < 0.5:
            return gray_array
        # Ignora correções absurdas (provavelmente detecção errada)
        if abs(angle) > 15:
            return gray_array

        h, w = gray_array.shape
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(
            gray_array, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception:
        return gray_array


def _preprocess_image(img: Image.Image) -> Image.Image:
    """Pré-processa imagem para melhorar OCR."""
    # 1) Orientação EXIF (rotação automática de fotos)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # 2) Resize
    largest = max(img.size)
    if largest > MAX_OCR_DIM:
        ratio = MAX_OCR_DIM / largest
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # 3) Grayscale
    if img.mode != "L":
        img = img.convert("L")

    # Caminho avançado com OpenCV (deskew + denoise + Otsu)
    if _CV2:
        try:
            arr = np.array(img)
            # 4) Deskew
            arr = _deskew(arr)
            # 5) Denoise leve (h=7 é suave; mais alto borra texto pequeno)
            arr = cv2.fastNlMeansDenoising(arr, h=7, templateWindowSize=7, searchWindowSize=21)
            # 6) Binarização Otsu — preto/branco automático
            _, arr = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return Image.fromarray(arr)
        except Exception:
            pass  # Fallback para PIL puro abaixo

    # Fallback PIL: auto-contraste compensa iluminação ruim
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
    Extrai texto de PDF ou imagem.
    Retorna (texto_extraido, metodo) onde metodo é 'direct' ou 'ocr'.
    """
    ext = Path(file_path).suffix.lower()

    if ext in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"):
        if on_progress:
            on_progress(0.3, "Processando imagem com OCR avançado...")
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
