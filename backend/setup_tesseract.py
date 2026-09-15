"""Download and verify the official Vietnamese/English tessdata_best files."""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.request

from dotenv import load_dotenv

from app.tesseract_models import ASSET_HASHES, asset_url, model_directory, model_valid, require_models


def setup():
    load_dotenv(Path(__file__).resolve().parent / ".env")
    folder = model_directory()
    folder.mkdir(parents=True, exist_ok=True)
    for name, expected in ASSET_HASHES.items():
        target = folder / name
        if model_valid(target, expected):
            print(f"Verified cached model: {name}", flush=True)
            continue
        url = asset_url(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading tessdata_best: {name}...", flush=True)
        with tempfile.TemporaryDirectory(prefix=".download-", dir=folder) as temporary:
            downloaded = Path(temporary) / target.name
            digest = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=60) as response, downloaded.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                raise RuntimeError(f"Checksum mismatch for {name}; previous file preserved. Run setup again.")
            os.replace(downloaded, target)
    require_models()
    print(f"Tesseract best models ready: {folder}", flush=True)


def check_engine():
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont
    from app.pdf_reader import _tesseract
    pytesseract, language, config = _tesseract()
    image = Image.new("RGB", (500,80), "white")
    ImageDraw.Draw(image).text((10,10), "BEST 1234567890", fill="black", font=ImageFont.load_default(size=36))
    payload = pytesseract.image_to_pdf_or_hocr(image, extension="pdf", lang=language, config=f"{config} --psm 7", timeout=90)
    with pymupdf.open(stream=payload, filetype="pdf") as pdf:
        text = pdf[0].get_text().strip()
    if not text:
        raise RuntimeError("Tesseract best returned no text during the startup check.")
    print(f"Tesseract {pytesseract.get_tesseract_version()}: {language}, OEM 1; searchable PDF check: {text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Also verify that the Tesseract executable can OCR with these models.")
    args = parser.parse_args()
    setup()
    if args.check:
        check_engine()
