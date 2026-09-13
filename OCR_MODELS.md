# Tesseract và VietOCR

Tesseract vẫn là bộ OCR chính. Luồng mặc định đã trở lại render PDF 300 DPI và lọc nền ngưỡng 170; không dùng các tùy chọn tăng DPI/ảnh xám của đợt thử trước. Bật OCR trên giao diện luôn OCR mọi trang PDF, kể cả trang có lớp chữ.

## Chế độ phối hợp

Chế độ tùy chọn dùng Tesseract để tìm dòng, từ, ô bảng và đọc số liệu; VietOCR `vgg_seq2seq` đọc lại crop ảnh màu trước lọc nền. Model được tải về máy và chạy tại máy, không gửi hóa đơn đến dịch vụ bên ngoài.

Đề xuất VietOCR chỉ được dùng khi xác suất model ≥ 0,90 và khớp các chữ sau khi bỏ dấu. Chỉ sửa dấu; giữ chữ hoa/thường, dấu câu và token chứa chữ số (số tiền, MST, ký hiệu có số…). Không so trực tiếp confidence của hai model. Trường hợp Tesseract bỏ sót vùng hoặc nhận nhầm chữ hoàn toàn vẫn cần sửa tay. Các từ lặp lại có cách đọc mâu thuẫn được giữ nguyên trong nhánh văn bản toàn trang.

Đây là chế độ thử nghiệm để đối chiếu trên hóa đơn thực, không bảo đảm luôn tốt hơn Tesseract. Kết quả vẫn cần kiểm tra tên, địa chỉ, mô tả và số liệu. Cảnh báo trên bản nháp cho biết mỗi trang đã đối chiếu bao nhiêu vùng; lỗi model có cảnh báo và log, các vùng chưa được bổ trợ giữ kết quả Tesseract.

## Bật trên Windows

Cài và chạy backend theo README trước. Tại thư mục repository:

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.vietocr.txt
.\.venv\Scripts\python.exe backend/setup_vietocr.py
$env:OCR_VIETOCR = "true"
$env:VIETOCR_DEVICE = "auto"
```

Sau đó chạy lại lệnh backend của lựa chọn SQLite hoặc SQL Server trong **cùng cửa sổ PowerShell**. `auto` chọn GPU CUDA nếu PyTorch hỗ trợ, nếu không dùng CPU. Có thể đặt `VIETOCR_DEVICE=cpu` để so sánh. Trọng số nằm trong `backend/models/vietocr/`, được gitignore; `VIETOCR_MODEL_DIR` cho phép đặt thư mục khác.

Để so sánh Tesseract cũ, đặt `$env:OCR_VIETOCR = "false"`, khởi động lại backend rồi upload lại cùng file. Không cần xóa model. Không dùng `pip install vietocr` riêng: bản PyPI 0.3.13 ghim Pillow 10.2, không phù hợp với bộ thư viện hiện tại. File requirements dùng bản upstream đã ghim commit để tránh lỗi đó.

## Bật trên Colab

Trong `Receipt_Reader_Colab.ipynb`, đánh dấu **USE_VIETOCR** ở ô cài đặt (ô code thứ hai), rồi chạy ô đó và ô khởi động. Mặc định tắt để giữ kết quả Tesseract cũ. Model được tải và kiểm tra ở bước cài đặt; lỗi sẽ hiện trước khi mở link demo. File model nằm tại `/content/receipt_reader_models/vietocr`, còn trong cùng runtime nhưng mất khi Colab xóa runtime. GPU là tùy chọn; CPU chậm hơn.

## Bộ tiếng Việt của Tesseract hiện tại

App dùng `vie+eng` tìm thấy trong `backend/tessdata/` nếu thư mục đó tồn tại, hoặc bộ dữ liệu của Tesseract được cài trên máy. Không có trọng số tiếng Việt đóng gói trong repository, nên tên `vie` hay phiên bản Tesseract không chứng minh máy đang dùng bộ tốt nhất. Notebook cài gói hệ thống, không chủ động tải `tessdata_best`.

Theo [tài liệu Tesseract](https://tesseract-ocr.github.io/tessdoc/Data-Files.html), `tessdata_fast` ưu tiên tốc độ và thường được phân phối cùng Linux; `tessdata_best` cho kết quả tốt hơn trong bộ đánh giá của tác giả nhưng chậm hơn. Điều đó không bảo đảm tốt hơn cho mọi hóa đơn tiếng Việt. Đợt sửa này giữ nguyên trọng số để không trộn thay đổi model với việc hoàn tác tiền xử lý ảnh.

VietOCR là bộ nhận dạng dòng chữ; API chính thức nhận một crop ảnh, không tự đọc bố cục hóa đơn. Phần phối hợp Tesseract + VietOCR và quy tắc chọn dấu ở đây do app thực hiện, không phải một pipeline có sẵn được xác nhận trong VietOCR. Tham khảo [VietOCR chính thức](https://github.com/pbcquoc/vietocr) và [Predictor](https://github.com/pbcquoc/vietocr/blob/fe8c3a7fc714aec57ab81cec844eb3adf0c1636c/vietocr/tool/predictor.py).
