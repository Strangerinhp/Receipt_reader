"""Optional accent correction; Tesseract remains the layout/number reader."""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
import logging
import math
import os
from pathlib import Path
import re
import unicodedata

log = logging.getLogger(__name__)
MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "vietocr"


@lru_cache(maxsize=2)
def load_predictor(model_dir: str, device: str):
    import torch
    from vietocr.tool.config import Cfg
    from vietocr.tool.predictor import Predictor

    folder = Path(model_dir)
    if not (folder / "config.yml").is_file() or not (folder / "weights.pth").is_file():
        raise RuntimeError("Chưa tải model; chạy python backend/setup_vietocr.py trước.")
    config = Cfg.load_config_from_file(str(folder / "config.yml"))
    config["weights"] = str(folder / "weights.pth")
    config["device"] = ("cuda:0" if torch.cuda.is_available() else "cpu") if device == "auto" else device
    config["cnn"]["pretrained"] = False  # The full checkpoint already contains CNN weights.
    config["predictor"]["beamsearch"] = False
    torch.set_num_threads(2)
    return Predictor(config)


def _fold(text):
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return "".join(c for c in text if not unicodedata.combining(c))


def merge_accents(words, prediction, probability):
    """Accept only matching letters/punctuation; never change a token with digits."""
    if not math.isfinite(float(probability)) or float(probability) < .90:
        return words
    prediction = unicodedata.normalize("NFC", prediction)
    original = " ".join(words)
    tokens = re.findall(r"\w+|[^\w\s]", original)
    proposed = re.findall(r"\w+|[^\w\s]", prediction)
    if len(tokens) != len(proposed) or any(_fold(a) != _fold(b) for a, b in zip(tokens, proposed)):
        return words
    replacements = []
    for old, new in zip(tokens, proposed):
        if not old.isalpha() or len(old) != len(new):
            replacements.append(old)
        else:
            replacements.append("".join(b.upper() if a.isupper() else b.lower() for a, b in zip(old, new)))
    iterator = iter(replacements)
    return [re.sub(r"\w+|[^\w\s]", lambda _: next(iterator), word) for word in words]


def replace_unambiguous(text, pairs):
    """Keep spacing and leave repeated words with conflicting readings untouched."""
    choices = defaultdict(set)
    for old, new in pairs:
        for a, b in zip(re.findall(r"\w+", old), re.findall(r"\w+", new)):
            choices[a].add(b)
    mapping = {old: next(iter(values)) for old, values in choices.items() if len(values) == 1}
    return re.sub(r"\w+", lambda match: mapping.get(match[0], match[0]), text)


class VietOCRAssist:
    def __init__(self):
        self.enabled = os.getenv("OCR_VIETOCR", "false").lower() in {"1", "true", "yes", "on"}
        self.failed = False
        self.checked = 0
        self.changed = 0

    def refine(self, image, words):
        """words: (text, pixel_bbox, line_id); return text at the same positions."""
        output = [word[0] for word in words]
        if not self.enabled or self.failed:
            return output
        lines = defaultdict(list)
        for i, (text, box, line) in enumerate(words):
            if text.strip():
                lines[line].append(i)
        try:
            predictor = None
            for indices in lines.values():
                # Split large gaps (columns) and long lines before recognition.
                segments, segment = [], []
                for index in sorted(indices, key=lambda i: words[i][1][0]):
                    box = words[index][1]
                    if segment:
                        previous = words[segment[-1]][1]
                        if box[0] - previous[2] > 3 * max(box[3] - box[1], previous[3] - previous[1]) or sum(len(words[i][0]) + 1 for i in segment) + len(words[index][0]) > 80:
                            segments.append(segment)
                            segment = []
                    segment.append(index)
                if segment:
                    segments.append(segment)
                for segment in segments:
                    texts = [words[i][0] for i in segment]
                    if sum(c.isalpha() for c in " ".join(texts)) < 3:
                        continue
                    boxes = [words[i][1] for i in segment]
                    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
                    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
                    pad = max(3, int((y1 - y0) * .15))
                    crop = image.crop((max(0, int(x0) - pad), max(0, int(y0) - pad),
                                       min(image.width, math.ceil(x1) + pad), min(image.height, math.ceil(y1) + pad)))
                    if crop.width <= 0 or crop.height <= 0:
                        continue
                    if predictor is None:
                        predictor = load_predictor(os.getenv("VIETOCR_MODEL_DIR") or str(MODEL_DIR),
                                                   os.getenv("VIETOCR_DEVICE", "auto"))
                    prediction, probability = predictor.predict(crop.convert("RGB"), return_prob=True)
                    corrected = merge_accents(texts, prediction, probability)
                    self.checked += 1
                    for index, new in zip(segment, corrected):
                        self.changed += new != output[index]
                        output[index] = new
        except Exception:
            # Optional recognition must not discard a completed Tesseract page.
            log.exception("VietOCR support failed; keeping Tesseract readings")
            self.failed = True
        return output

    def refine_data(self, image, data):
        words = [(text, (data["left"][i], data["top"][i], data["left"][i] + data["width"][i],
                         data["top"][i] + data["height"][i]),
                  (data["block_num"][i], data["par_num"][i], data["line_num"][i]))
                 for i, text in enumerate(data["text"])]
        return self.refine(image, words)

    def refine_pdf(self, image, page, text, tables):
        sx, sy = image.width / page.rect.width, image.height / page.rect.height
        original = page.get_text("words")
        words = [(w[4], (w[0] * sx, w[1] * sy, w[2] * sx, w[3] * sy), (w[5], w[6])) for w in original]
        corrected = self.refine(image, words)
        pairs = list(zip([w[4] for w in original], corrected))
        text = replace_unambiguous(text, pairs)
        for table in tables:
            for row, box in zip(table["rows"], table["bboxes"]):
                row_pairs = [pair for word, pair in zip(original, pairs)
                             if box[0] <= (word[0] + word[2]) / 2 <= box[2] and box[1] <= (word[1] + word[3]) / 2 <= box[3]]
                row[:] = [replace_unambiguous(value, row_pairs) if value else value for value in row]
        return text

    def message(self, page_number):
        if not self.enabled:
            return []
        if self.failed:
            return [f"Trang {page_number}: VietOCR bị lỗi hoặc chưa được cài/tải model; các vùng chưa xử lý giữ kết quả Tesseract. Xem log backend."]
        return [f"Trang {page_number}: Tesseract + VietOCR đã đối chiếu {self.checked} vùng chữ; chỉ chấp nhận sửa dấu khi phần chữ khớp. Cần kiểm tra lại tên, địa chỉ và mô tả."]
