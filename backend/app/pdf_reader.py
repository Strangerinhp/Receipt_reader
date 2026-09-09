"""Read native PDF geometry; OCR only pages without a usable text layer."""
from __future__ import annotations

import io
import os
import re
from statistics import median
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps, ImageSequence

from .invoice_tables import apply_tables, decimal_value, header_columns, validate_document
from .invoice_text import compact, document_from_text, label_values


def _tables(page, page_number: int, method: str, add_lines=None) -> list[dict]:
    result = []
    finder = page.find_tables(add_lines=add_lines)
    for table in finder.tables:
        rows = table.extract()
        if not any(header_columns([compact(v) for v in row]) for row in rows):
            continue
        result.append({"page": page_number, "method": method, "rows": rows,
                       "bboxes": [list(row.bbox) for row in table.rows]})
    return result


def _usable_text(page, text: str) -> bool:
    if len(text.strip()) < 40 or text.count("\ufffd") > len(text) * 0.01:
        return False
    words = page.get_text("words")
    if len(words) < 10:
        return False
    # A page-sized scan can have only a searchable footer or signature overlay.
    image_area = max((pymupdf.Rect(info["bbox"]).get_area() for info in page.get_image_info()), default=0)
    if image_area > page.rect.get_area() * 0.65 and len(words) < 80:
        return False
    return True


def _tesseract():
    import pytesseract
    if os.getenv("TESSERACT_CMD"):
        pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
    local = Path(__file__).resolve().parents[1] / "tessdata"
    config = f'--tessdata-dir "{local}"' if local.exists() else ""
    try:
        languages = set(pytesseract.get_languages(config=config))
    except Exception as exc:
        raise RuntimeError("Không tìm thấy Tesseract OCR. Hãy cài Tesseract và cấu hình TESSERACT_CMD.") from exc
    language = "+".join(lang for lang in ("vie", "eng") if lang in languages)
    if not language:
        raise RuntimeError("Tesseract cần language pack vie hoặc eng.")
    return pytesseract, language, config


def _prepare_image(image):
    import cv2
    import numpy as np
    image = ImageOps.exif_transpose(image).convert("RGB")
    # Bound processing memory for very large camera images.
    if max(image.size) > 4500:
        image.thumbnail((4500, 4500))
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    segments = cv2.HoughLinesP(mask, 1, np.pi / 1800, 100,
                              minLineLength=image.width // 4, maxLineGap=20)
    if segments is not None:
        angles = [np.degrees(np.arctan2(y2 - y1, x2 - x1)) for [[x1, y1, x2, y2]] in segments]
        angles = [a for a in angles if abs(a) <= 7]
        if angles:
            angle = float(np.median(angles))
            if abs(angle) > 0.15:
                image = image.rotate(angle, expand=True, fillcolor="white", resample=Image.Resampling.BICUBIC)
    return image


def _grid_lines(image, page):
    """Recover long raster rules as virtual PDF lines for the table detector."""
    import cv2
    import numpy as np
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, 35, 15)
    lines = []
    sx, sy = page.rect.width / image.width, page.rect.height / image.height
    for horizontal in (True, False):
        length = max(30, (image.width if horizontal else image.height) // 30)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (length, 1) if horizontal else (1, length))
        joined = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                                 cv2.getStructuringElement(cv2.MORPH_RECT, (12, 1) if horizontal else (1, 8)))
        rules = cv2.morphologyEx(joined, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(rules, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if horizontal and w >= length and w > 5 * h:
                lines.append(((x * sx, (y + h / 2) * sy), ((x + w) * sx, (y + h / 2) * sy)))
            elif not horizontal and h >= length and h > 5 * w:
                lines.append((((x + w / 2) * sx, y * sy), ((x + w / 2) * sx, (y + h) * sy)))
    return lines


def _raster_cells(image):
    """Locate a ruled item table by columns sharing their top boundary.

    This also joins dotted horizontal rules. Page borders and QR codes do not
    qualify: at least six long, aligned vertical rules are required.
    """
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=image.width, height=image.height)
        lines = _grid_lines(image, page)
    vertical = [(a[0], min(a[1], b[1]), max(a[1], b[1])) for a, b in lines
                if abs(a[0] - b[0]) < 1 and abs(a[1] - b[1]) > image.height * .15]
    groups = [[v for v in vertical if abs(v[1] - anchor[1]) < image.height * .012] for anchor in vertical]
    groups = [g for g in groups if len(g) >= 6]
    if not groups:
        return None
    group = max(groups, key=len)
    def cluster(values, tolerance=8):
        clusters = []
        for value in sorted(values):
            if clusters and value - clusters[-1][-1] <= tolerance:
                clusters[-1].append(value)
            else:
                clusters.append([value])
        return [median(c) for c in clusters]
    xs = cluster([v[0] for v in group])
    top, bottom = median(v[1] for v in group), min(v[2] for v in group)
    if len(xs) < 6 or xs[-1] - xs[0] < image.width * .5:
        return None
    ys = [a[1] for a, b in lines if abs(a[1] - b[1]) < 1 and
          abs(a[0] - b[0]) > (xs[-1] - xs[0]) * .5 and top - 8 <= a[1] <= bottom + 8]
    ys = cluster([top, *ys, bottom])
    if len(ys) < 3:
        return None
    return xs, ys


def _ocr_cell_batches(image, boxes, pytesseract, language, config):
    """OCR isolated cells in padded batches, keeping exact cell membership."""
    results = []
    for offset in range(0, len(boxes), 18):
        batch = boxes[offset:offset + 18]
        crops = [image.crop((int(x0) + 4, int(y0) + 4, int(x1) - 4, int(y1) - 4)) for x0, y0, x1, y1 in batch]
        atlas = Image.new("RGB", (max(c.width for c in crops) + 60, sum(c.height + 50 for c in crops)), "white")
        regions, y = [], 20
        for crop in crops:
            atlas.paste(crop, (25, y))
            regions.append((y, y + crop.height))
            y += crop.height + 50
        data = pytesseract.image_to_data(atlas, lang=language, config=f"{config} --psm 6 --dpi 300",
                                         output_type=pytesseract.Output.DICT, timeout=90)
        cells = [[] for _ in batch]
        for i, text in enumerate(data["text"]):
            if not text.strip():
                continue
            center = data["top"][i] + data["height"][i] / 2
            for index, (start, end) in enumerate(regions):
                if start <= center <= end:
                    cells[index].append((data["top"][i], data["left"][i], text, float(data["conf"][i])))
                    break
        for cell in cells:
            # Tesseract already emits reading order within a cell.
            results.append((" ".join(w[2] for w in cell), min((w[3] for w in cell), default=0)))
    return results


def _ocr_ruled_table(image, geometry, page_number, pytesseract, language, config, rule_image=None):
    xs, ys = geometry
    # Header confirmation comes first. Then STT anchors recover faint/dotted row
    # boundaries, which may be visible only in part of the description column.
    header_boxes = [(x0, y0, x1, y1) for y0, y1 in zip(ys[:2], ys[1:3]) for x0, x1 in zip(xs, xs[1:])]
    header_cells = _ocr_cell_batches(image, header_boxes, pytesseract, language, config)
    columns = len(xs) - 1
    header_rows = [[c[0] for c in header_cells[i:i + columns]] for i in range(0, len(header_cells), columns)]
    if not header_columns(header_rows[0]):
        return None
    mapping = header_columns(header_rows[0])
    formula = len(header_rows) > 1 and re.fullmatch(r"\(?2\)?", header_rows[1][mapping["THHDVu"]].strip())
    start = ys[2] if formula else ys[1]
    col = mapping["STT"]
    index_image = image.crop((int(xs[col]) + 4, int(start) + 4, int(xs[col + 1]) - 4, int(ys[-1]) - 4))
    index_data = pytesseract.image_to_data(index_image, lang="eng" if "eng" in language else language,
                                          config=f"{config} --psm 6 -c tessedit_char_whitelist=0123456789",
                                          output_type=pytesseract.Output.DICT, timeout=90)
    anchors = [start + 4 + index_data["top"][i] + index_data["height"][i] / 2
               for i, word in enumerate(index_data["text"]) if re.fullmatch(r"\d+", word.strip())]
    if len(anchors) > 1:
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=image.width, height=image.height)
            lines = _grid_lines(rule_image or image, page)
        candidates = {}
        for a, b in lines:
            if abs(a[1] - b[1]) < 1 and start < a[1] < ys[-1]:
                key = round(a[1] / 6) * 6
                candidates.setdefault(key, []).append((max(xs[0], min(a[0], b[0])), min(xs[-1], max(a[0], b[0]))))
        def coverage(intervals):
            end, total = xs[0], 0
            for left, right in sorted(intervals):
                if right > max(left, end):
                    total += right - max(left, end)
                    end = right
            return total
        boundaries = []
        for lower, upper in zip(anchors, anchors[1:]):
            possible = [y for y, spans in candidates.items() if lower + 4 < y < upper - 4 and coverage(spans) > (xs[-1] - xs[0]) * .3]
            if not possible:
                # Do not manufacture row boundaries when neither rules nor layout support them.
                return None
            boundaries.append(max(possible, key=lambda y: (coverage(candidates[y]), -abs(y - (lower + upper) / 2))))
        tail = [y for y in ys if y > anchors[-1] + 5]
        ys = [*ys[:2 if formula else 1], start, *boundaries, *tail]
    boxes = [(x0, y0, x1, y1) for y0, y1 in zip(ys, ys[1:]) for x0, x1 in zip(xs, xs[1:])]
    cells = _ocr_cell_batches(image, boxes, pytesseract, language, config)
    rows = [[cell[0] for cell in cells[i:i + columns]] for i in range(0, len(cells), columns)]
    # Keep the result only when OCR confirms that the grid is an invoice table.
    if not any(header_columns(row) for row in rows[:2]):
        return None
    table = {"page": page_number, "method": "OCR cells", "rows": rows,
             "bboxes": [[xs[0] * .24, y0 * .24, xs[-1] * .24, y1 * .24] for y0, y1 in zip(ys, ys[1:])],
             "confidence": [[cell[1] for cell in cells[i:i + columns]] for i in range(0, len(cells), columns)]}
    return table


def ocr_page(image, page_number: int) -> tuple[str, list[dict], list[str]]:
    pytesseract, language, config = _tesseract()
    warnings = []
    if "vie" not in language:
        warnings.append(f"Trang {page_number}: thiếu language pack vie, OCR đang dùng tiếng Anh.")
    image = _prepare_image(image)
    try:
        osd = pytesseract.image_to_osd(image, config=config, output_type=pytesseract.Output.DICT, timeout=15)
        if osd.get("orientation_conf", 0) >= 5 and osd.get("rotate"):
            image = image.rotate(-int(osd["rotate"]), expand=True, fillcolor="white")
    except (pytesseract.TesseractError, RuntimeError):
        pass  # Orientation detection is optional on sparse pages.
    geometry = _raster_cells(image)
    # Pale colored watermarks interfere with table columns; retain dark ink.
    clean_image = ImageOps.grayscale(image).point(lambda value: 255 if value > 170 else 0).convert("RGB")
    if geometry:
        try:
            table = _ocr_ruled_table(clean_image, geometry, page_number, pytesseract, language, config, rule_image=image)
            if table:
                xs, ys = geometry
                header = clean_image.crop((int(xs[0]), 0, int(xs[-1]), int(ys[0]) - 3))
                footer = clean_image.crop((int(xs[0]), int(ys[-1]) + 3, int(xs[-1]), image.height))
                texts = [pytesseract.image_to_string(header, lang=language, config=f"{config} --psm 3", timeout=90),
                         "\n".join(" | ".join(row) for row in table["rows"]),
                         pytesseract.image_to_string(footer, lang=language, config=f"{config} --psm 6", timeout=90)]
                warnings.append(f"Trang {page_number} dùng OCR theo ô; cần đối chiếu chữ và số với ảnh gốc.")
                return "\n".join(texts), [table], warnings
        except (pytesseract.TesseractError, RuntimeError, ValueError):
            warnings.append(f"Trang {page_number}: OCR theo ô chưa thành công, đã dùng OCR toàn trang.")
    try:
        payload = pytesseract.image_to_pdf_or_hocr(clean_image, extension="pdf", lang=language,
                                                  config=f"{config} --psm 3 --dpi 300", timeout=90)
    except (pytesseract.TesseractError, RuntimeError) as exc:
        raise RuntimeError(f"OCR trang {page_number} thất bại hoặc quá thời gian: {exc}") from exc
    with pymupdf.open(stream=payload, filetype="pdf") as pdf:
        page = pdf[0]
        text = page.get_text(sort=True)
        tables = _tables(page, page_number, "OCR table", _grid_lines(image, page))
    warnings.append(f"Trang {page_number} dùng OCR; cần đối chiếu chữ và số với ảnh gốc.")
    return text, tables, warnings


def _finish(texts, tables, warnings, ocr_used):
    text = "\n\f\n".join(texts).strip()
    document = document_from_text(text)
    apply_tables(document, tables, warnings)
    content = document["NDHDon"]
    totals = content["TToan"]
    # A single global VAT rate in six-column invoice layouts applies to all items.
    rates = {value for label, value in label_values(text) if label == "rate" and re.fullmatch(r"\d+(?:,\d+)?%", value)}
    if len(rates) == 1 and not totals["THTTLTSuat"]:
        rate = next(iter(rates))
        if totals["TgTCThue"] and totals["TgTThue"]:
            totals["THTTLTSuat"] = [{"TSuat": rate, "ThTien": totals["TgTCThue"], "TThue": totals["TgTThue"]}]
        for item in content["DSHHDVu"]:
            if item["TChat"] == "1" and not item["TSuat"]:
                item["TSuat"] = rate
    items = [item for item in content["DSHHDVu"] if item["TChat"] == "1"]
    if len(items) == 1 and not items[0]["TThue"] and totals["TgTThue"]:
        amount = decimal_value(items[0]["ThTien"])
        if amount is not None and amount == decimal_value(totals["TgTCThue"]):
            items[0]["TThue"] = totals["TgTThue"]
            items[0]["TTKhac"].append({"TTruong": "Nguồn tiền thuế dòng", "KDLieu": "string",
                                      "DLieu": "Tổng thuế hóa đơn chỉ có một dòng hàng và thành tiền khớp tổng trước thuế"})
    if not document["NDHDon"]["DSHHDVu"] and text:
        warnings.append("Chưa nhận diện được dòng hàng trong bảng; cần kiểm tra và bổ sung từ file gốc.")
    warnings.extend(validate_document(document))
    missing = [name for key, name in (("SHDon", "số hóa đơn"), ("NLap", "ngày lập")) if not document["TTChung"][key]]
    if text and missing:
        warnings.append("Chưa đọc được " + ", ".join(missing) + "; cần kiểm tra file gốc.")
    return document, text, list(dict.fromkeys(warnings)), ocr_used


def read_pdf(payload: bytes, use_ocr: bool):
    texts, tables, warnings = [], [], []
    ocr_used = False
    try:
        pdf = pymupdf.open(stream=payload, filetype="pdf")
    except (RuntimeError, ValueError) as exc:
        raise ValueError("Không thể mở PDF: file hỏng hoặc không đúng định dạng.") from exc
    with pdf:
        if pdf.needs_pass:
            raise ValueError("PDF được bảo vệ bằng mật khẩu. Hãy tải bản PDF đã mở khóa.")
        for page in pdf:
            number = page.number + 1
            text = page.get_text(sort=True)
            if _usable_text(page, text):
                try:
                    tables.extend(_tables(page, number, "PDF table"))
                except Exception:
                    warnings.append(f"Trang {number}: không phân tích được bảng; đã giữ văn bản để kiểm tra.")
            elif use_ocr:
                pixmap = page.get_pixmap(dpi=300, alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                text, page_tables, page_warnings = ocr_page(image, number)
                tables.extend(page_tables)
                warnings.extend(page_warnings)
                ocr_used = True
            else:
                warnings.append(f"Trang {number}: lớp chữ thiếu hoặc không đủ rõ. Hãy bật OCR cho trang scan.")
                # Retain text for review, but do not map a sparse footer as invoice data.
                text = ""
            texts.append(text)
    return _finish(texts, tables, warnings, ocr_used)


def read_image(payload: bytes):
    texts, tables, warnings = [], [], []
    try:
        source = Image.open(io.BytesIO(payload))
    except Exception as exc:
        raise ValueError("Không thể đọc input này như một ảnh.") from exc
    with source:
        for number, frame in enumerate(ImageSequence.Iterator(source), 1):
            text, page_tables, page_warnings = ocr_page(frame.copy(), number)
            texts.append(text)
            tables.extend(page_tables)
            warnings.extend(page_warnings)
    return _finish(texts, tables, warnings, True)
