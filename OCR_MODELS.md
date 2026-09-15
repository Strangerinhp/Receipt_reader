# Tesseract best

App dùng `vie.traineddata` và `eng.traineddata` từ [tessdata_best chính thức](https://github.com/tesseract-ocr/tessdata_best), với chế độ LSTM (`--oem 1`). Model `osd` chỉ dùng để nhận diện hướng trang, chạy riêng bằng `--oem 0`.

Model được ghim ở commit `e12c65a915945e4c28e237a9b52bc4a8f39a0cec`. Bộ tải còn lấy `configs/pdf` và `pdf.ttf` từ Tesseract 5.3.4 để nhánh OCR toàn trang xuất được PDF có lớp chữ. Bộ tải và backend cùng kiểm tra SHA-256 của cả năm file trong `backend/app/tesseract_models.py`, bảo đảm local và Colab dùng cùng trọng số. Thiếu hoặc sai file sẽ báo lỗi; không tự chuyển sang gói `fast` của hệ thống.

## Local

Cài backend theo lựa chọn SQLite hoặc Microsoft SQL Server trong README, rồi tải model:

```powershell
.\.venv\Scripts\python.exe backend/setup_tesseract.py
```

Mặc định lưu tại `backend/models/tessdata_best/`. Có thể đặt `TESSERACT_MODEL_DIR` trước khi chạy cả setup và backend nếu muốn dùng thư mục khác. Các file model được gitignore. Tải lần đầu khoảng 38 MB; lần sau kiểm tra checksum và dùng lại file hợp lệ. Khi tải lỗi hoặc checksum không khớp, file đang có không bị ghi đè.

Kiểm tra Tesseract thực sự đọc được bộ best:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
.\.venv\Scripts\python.exe backend/setup_tesseract.py --check
```

Sau khi cập nhật, khởi động lại backend rồi upload lại hóa đơn. Hóa đơn đã lưu không được OCR lại tự động.

## Colab

Notebook tự tải model và chạy kiểm tra OCR trong ô cài đặt. Không cần chọn model hoặc bật GPU. Thư mục model là `/content/receipt_reader_models/tessdata_best`, tách khỏi thư mục clone để dùng lại sau khi cập nhật mã nguồn trong cùng runtime. Colab xóa runtime thì cần tải lại.

Dừng demo cũ bằng ô `STOP_DEMO`, tải notebook mới rồi chạy lần lượt ba ô code đầu. Các ô cài đặt và khởi động sử dụng cùng `TESSERACT_MODEL_DIR`.

## Hành vi OCR

Bật OCR trên giao diện sẽ nhận dạng mọi trang PDF. Ảnh vẫn render 300 DPI, giới hạn cạnh dài 4.500 pixel, chỉnh hướng/nghiêng và lọc nền ngưỡng 170. Tesseract đọc toàn bộ chữ và ô bảng; các bước ánh xạ trường, kiểm tra số liệu và hiển thị vẫn theo [PDF_PROCESSING.md](PDF_PROCESSING.md).

Theo [tài liệu Tesseract](https://tesseract-ocr.github.io/tessdoc/Data-Files.html), bộ best ưu tiên độ chính xác và chạy chậm hơn bộ fast. Điều này không bảo đảm đọc đúng mọi dấu hoặc bảng của hóa đơn; cần đối chiếu kết quả với file gốc.
