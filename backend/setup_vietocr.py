"""Download the official seq2seq assets before starting OCR (no invoice upload)."""
from pathlib import Path
import os
import shutil
import urllib.request

import yaml

REVISION = "fe8c3a7fc714aec57ab81cec844eb3adf0c1636c"


def setup():
    folder = Path(os.getenv("VIETOCR_MODEL_DIR") or Path(__file__).resolve().parent / "models" / "vietocr")
    folder.mkdir(parents=True, exist_ok=True)
    config = {}
    for name in ("base.yml", "vgg-seq2seq.yml"):
        url = f"https://raw.githubusercontent.com/pbcquoc/vietocr/{REVISION}/config/{name}"
        with urllib.request.urlopen(url, timeout=60) as response:
            config.update(yaml.safe_load(response.read().decode("utf-8")))
    target = folder / "weights.pth"
    if not target.is_file():
        temporary = target.with_suffix(".download")
        try:
            print("Downloading official VietOCR seq2seq weights...", flush=True)
            with urllib.request.urlopen(config["weights"], timeout=60) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    config["weights"] = str(target.resolve())
    config["cnn"]["pretrained"] = False
    config["device"] = "cpu"
    config["predictor"]["beamsearch"] = False
    (folder / "config.yml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    # Fail at setup, rather than during a user's long invoice request.
    from app.vietocr_assist import load_predictor
    predictor = load_predictor(str(folder.resolve()), os.getenv("VIETOCR_DEVICE", "auto"))
    print(f"VietOCR ready: {predictor.device}; model directory: {folder.resolve()}")


if __name__ == "__main__":
    setup()
