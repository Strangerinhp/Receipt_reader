"""Map Google Vision word boxes to reading lines and ruled invoice cells."""
from bisect import bisect_right
from statistics import median

from PIL import ImageOps

from .invoice_tables import header_columns


def reading_lines(words):
    """Group nearby baselines, then read left to right without layout padding."""
    lines = []
    for word in sorted(words, key=lambda w: ((w["bbox"][1] + w["bbox"][3]) / 2, w["bbox"][0])):
        box = word["bbox"]
        center = (box[1] + box[3]) / 2
        height = max(1, box[3] - box[1])
        if lines and abs(center - lines[-1]["center"]) <= .45 * min(height, lines[-1]["height"]):
            line = lines[-1]
            line["words"].append(word)
            line["center"] = median((w["bbox"][1] + w["bbox"][3]) / 2 for w in line["words"])
        else:
            lines.append({"center": center, "height": height, "words": [word]})
    return "\n".join(" ".join(w["text"] for w in sorted(line["words"], key=lambda w: w["bbox"][0]))
                     for line in lines)


def ruled_table(words, geometry, number):
    xs, ys = geometry
    cells = [[[] for _ in range(len(xs) - 1)] for _ in range(len(ys) - 1)]
    for word in words:
        x0, y0, x1, y1 = word["bbox"]
        column = bisect_right(xs, (x0 + x1) / 2) - 1
        row = bisect_right(ys, (y0 + y1) / 2) - 1
        if 0 <= row < len(cells) and 0 <= column < len(cells[row]):
            cells[row][column].append(word)
    rows = [[reading_lines(cell) for cell in row] for row in cells]
    if not any(header_columns(row) for row in rows[:2]):
        return None
    return {
        "page": number, "method": "Google Vision cells", "rows": rows,
        "bboxes": [[xs[0] * .24, y0 * .24, xs[-1] * .24, y1 * .24] for y0, y1 in zip(ys, ys[1:])],
        "confidence": [[min((w["confidence"] for w in cell), default=0) for cell in row] for row in cells],
    }


def extract_page(image, number, reader, detect_grid):
    warnings = [f"Trang {number} dùng Google Cloud Vision; cần đối chiếu chữ và số với ảnh gốc."]
    with ImageOps.exif_transpose(image).convert("RGB") as prepared:
        raw_text, words = reader.recognize(prepared, number)
        text = reading_lines(words) if words else raw_text
        tables = []
        if words:
            try:
                geometry = detect_grid(prepared)
                table = ruled_table(words, geometry, number) if geometry else None
                if table:
                    tables.append(table)
                    xs, ys = geometry
                    def inside(word):
                        x0, y0, x1, y1 = word["bbox"]
                        return xs[0] <= (x0 + x1) / 2 <= xs[-1] and ys[0] <= (y0 + y1) / 2 <= ys[-1]
                    outside = [word for word in words if not inside(word)]
                    header = [word for word in outside if (word["bbox"][1] + word["bbox"][3]) / 2 < ys[0]]
                    footer = [word for word in outside if word not in header]
                    text = "\n".join([reading_lines(header),
                                      "\n".join(" | ".join(row) for row in table["rows"]),
                                      reading_lines(footer)])
            except Exception:
                warnings.append(f"Trang {number}: không phân tích được cấu trúc bảng Vision; đã giữ văn bản để kiểm tra.")
        if not tables:
            warnings.append(f"Trang {number}: chưa xác định được bảng có đường kẻ từ Vision; kiểm tra lại các dòng hàng.")
        if not text.strip():
            warnings.append(f"Trang {number}: Google Vision không nhận được văn bản.")
        return text, tables, warnings
