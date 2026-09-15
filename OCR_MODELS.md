# Cấu hình OCR

Phần nhận dạng được khôi phục theo commit `fc07435` ngày 10/09/2026, trước thử nghiệm model và upsampling. Giữ các sửa lỗi giao diện, tác vụ nền, tải kết quả qua Colab và quyền chọn OCR cho mọi trang PDF.

App dùng Tesseract đã cài tại máy. Nếu có `backend/tessdata`, dùng thư mục đó; nếu không, dùng gói ngôn ngữ hệ thống. Ưu tiên `vie+eng`; thiếu tiếng Việt thì cảnh báo và dùng tiếng Anh nếu có. Không còn bộ tải model riêng, ép OEM hoặc bộ nhận dạng bổ sung.

PDF render 300 DPI như mốc cũ. Ảnh không được phóng lớn thêm; cạnh dài quá 4.500 pixel được thu nhỏ, sau đó chỉnh nghiêng/hướng và lọc nền ngưỡng 170. Chi tiết tại [PDF_PROCESSING.md](PDF_PROCESSING.md).

## Local

Cài Tesseract cùng Vietnamese (`vie`) và English (`eng`), cấu hình `TESSERACT_CMD` theo [README.md](README.md). Kiểm tra gói đã cài:

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

Khởi động lại backend rồi upload lại hóa đơn; dữ liệu đã lưu không được OCR lại tự động. Chất lượng còn phụ thuộc phiên bản Tesseract và language pack tại máy.

## Colab

Notebook cài `tesseract-ocr`, `tesseract-ocr-vie`, `tesseract-ocr-eng` từ hệ thống. Ô cài đặt kiểm tra ngôn ngữ và chạy OCR mẫu tạo PDF có lớp chữ. Không cần GPU hoặc tải model riêng.

Để cập nhật runtime cũ: bật `STOP_DEMO` và chạy ô cuối, tải notebook mới, rồi chạy lần lượt ba ô code đầu. Thư mục model thử nghiệm cũ không còn được app tham chiếu. Các bản sửa tải cloudflared khi tunnel đang chạy, log cài đặt và polling kết quả được giữ nguyên.
