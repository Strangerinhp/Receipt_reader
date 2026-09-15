"""Pinned, verified Tesseract best models shared by setup and OCR."""
from functools import lru_cache
import hashlib
import os
from pathlib import Path

REVISION = "e12c65a915945e4c28e237a9b52bc4a8f39a0cec"
MODEL_HASHES = {
    "vie": "b6b49293d95d0b6dbd8780174627e82c75be957b6f4ed9862155540d6b00bb45",
    "eng": "8280aed0782fe27257a68ea10fe7ef324ca0f8d85bd2fd145d1c2b560bcb66ba",
    "osd": "9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff",
}
SUPPORT_REVISION = "5.3.4"
SUPPORT_HASHES = {
    "configs/pdf": "54d56e81dfefe289b0d2e4c7bc9bbe662711f5b8255c128b73bcd66efb6bba1a",
    "pdf.ttf": "c7845420925a23d88ed830a63957b8af85a66a8daf8d9fc90e843673b2ef1a59",
}
ASSET_HASHES = {**{f"{name}.traineddata": digest for name, digest in MODEL_HASHES.items()}, **SUPPORT_HASHES}


def asset_url(filename):
    if filename in SUPPORT_HASHES:
        return f"https://raw.githubusercontent.com/tesseract-ocr/tesseract/{SUPPORT_REVISION}/tessdata/{filename}"
    return f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/{REVISION}/{filename}"


def model_directory():
    return Path(os.getenv("TESSERACT_MODEL_DIR") or Path(__file__).resolve().parents[1] / "models" / "tessdata_best").resolve()


@lru_cache(maxsize=12)
def _digest(path, size, modified, changed):
    # Include file metadata in the cache key so replaced models are rechecked.
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def model_valid(path, expected):
    try:
        info = path.stat()
        return _digest(str(path), info.st_size, info.st_mtime_ns, info.st_ctime_ns) == expected
    except OSError:
        return False


def require_models():
    folder = model_directory()
    invalid = [name for name, digest in ASSET_HASHES.items() if not model_valid(folder / name, digest)]
    if invalid:
        raise RuntimeError(
            f"Thiếu hoặc sai model Tesseract best ({', '.join(invalid)}) tại {folder}. "
            "Chạy python backend/setup_tesseract.py rồi thử lại."
        )
    return folder


def tesseract_config(oem=1):
    # osd uses the legacy orientation detector (OEM 0); text uses LSTM (OEM 1).
    return f'--tessdata-dir "{require_models()}" --oem {oem}'
