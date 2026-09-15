"""Optional Google Cloud Vision engine, independent of Tesseract."""
import io
import os

from PIL import ImageOps


def enabled():
    return os.getenv("GOOGLE_VISION_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def validate_request(use_ocr, ocr_engine):
    if ocr_engine not in {"tesseract", "google_vision"}:
        raise ValueError("OCR engine phải là tesseract hoặc google_vision.")
    if use_ocr and ocr_engine == "google_vision" and not enabled():
        raise ValueError("Google Cloud Vision chưa được bật trên máy chủ. Xem GOOGLE_VISION.md.")


class VisionReader:
    def __init__(self):
        self.client = None

    def recognize(self, image, number):
        """One request per page, with no automatic retries or engine fallback."""
        if self.client is None:
            try:
                from google.cloud import vision
                self.client = vision.ImageAnnotatorClient()
            except ImportError:
                raise RuntimeError("Thiếu thư viện Google Vision. Cài backend/requirements.vision.txt.") from None
            except Exception:
                raise RuntimeError("Không khởi tạo được Google Vision. Kiểm tra Application Default Credentials trên máy chủ.") from None
        # Preserve the original pixels; do not run Tesseract preprocessing,
        # upsampling, binarization or orientation detection on this path.
        with ImageOps.exif_transpose(image).convert("RGB") as prepared:
            buffer = io.BytesIO()
            prepared.save(buffer, format="PNG")
            content = buffer.getvalue()
        if len(content) > 7 * 1024 * 1024:
            raise RuntimeError(f"Trang {number}: ảnh vượt giới hạn gửi Google Vision (7 MB PNG).")
        try:
            response = self.client.document_text_detection(
                image={"content": content}, image_context={"language_hints": ["vi", "en"]},
                timeout=60, retry=None,
            )
        except Exception:
            # Raw upstream exceptions may include credentials/project details.
            raise RuntimeError(f"Google Vision trang {number} không phản hồi thành công. Kiểm tra kết nối, quyền, billing và quota (timeout 60 giây).") from None
        if response.error.code or response.error.message:
            raise RuntimeError(f"Google Vision trang {number} trả lỗi mã {response.error.code}. Kiểm tra quyền, billing và quota.")
        annotation = response.full_text_annotation
        words = []
        for page in annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        text = "".join(symbol.text for symbol in word.symbols)
                        vertices = word.bounding_box.vertices
                        if text and vertices:
                            words.append({"text": text,
                                          "bbox": [min(v.x for v in vertices), min(v.y for v in vertices),
                                                   max(v.x for v in vertices), max(v.y for v in vertices)],
                                          "confidence": float(word.confidence) * 100})
        return annotation.text, words

    def close(self):
        if self.client is not None:
            try:
                self.client.transport.close()
            except Exception:
                pass
