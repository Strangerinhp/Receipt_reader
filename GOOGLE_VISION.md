# Google Cloud Vision OCR

Ở màn hình tải lên, bật OCR và chọn **Tesseract** hoặc **Google Cloud Vision**. Mặc định là Tesseract. Khi chọn Vision, chỉ Vision nhận dạng và điền dữ liệu; không chạy Tesseract, không tự đổi engine khi có lỗi. Tắt OCR thì PDF dùng lớp chữ như trước.

## Chuẩn bị Google Cloud

1. Chọn/tạo Google Cloud project, bật billing và **Cloud Vision API** theo [hướng dẫn Google](https://cloud.google.com/vision/docs/setup).
2. Cấu hình [Application Default Credentials (ADC)](https://cloud.google.com/vision/docs/authentication) cho máy chạy backend. Có thể dùng `gcloud auth application-default login` ở local, hoặc JSON service account của project. Với user ADC, đặt quota project bằng `gcloud auth application-default set-quota-project PROJECT_ID`; tài khoản cần quyền sử dụng dịch vụ trong project đó.
3. Nếu dùng JSON service account, lưu ngoài repo, ví dụ `C:\private\vision-service-account.json`. Không gửi khóa lên frontend hoặc commit Git. Biến `GOOGLE_APPLICATION_CREDENTIALS` trỏ tới file này; nếu dùng ADC của gcloud thì không đặt biến đó.

## Chạy local

Cài backend SQLite hoặc SQL Server theo README. Trong PowerShell chạy backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.vision.txt
$env:GOOGLE_VISION_ENABLED = "true"
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\private\vision-service-account.json"
.\.venv\Scripts\python.exe backend/run.py
```

Thay đường dẫn bằng file thật. Nếu dùng gcloud ADC, bỏ dòng đặt `GOOGLE_APPLICATION_CREDENTIALS`. Có thể lưu biến cấu hình trong `backend/.env` đã được gitignore. Khởi động lại backend sau khi đổi cấu hình. Không cần cài Tesseract nếu chỉ chọn Vision; các thư viện Python xử lý PDF/ảnh vẫn cần thiết.

## Google Colab

1. Dừng demo cũ, tải notebook mới.
2. Dùng bảng **Files** của Colab để tải JSON service account lên runtime, bên ngoài thư mục clone, ví dụ `/content/vision-service-account.json`.
3. Trong ô cài đặt, bật `ENABLE_GOOGLE_VISION` và đặt `GOOGLE_VISION_CREDENTIALS_PATH` tới file trên. Chạy lại các ô cài đặt/khởi động.
4. Mở link demo, bật OCR và chọn **Google Cloud Vision**.

Notebook kiểm tra SDK/khởi tạo credentials, không gọi OCR có tính phí ở bước cài đặt. Khi runtime bị xóa, cần tải khóa lên lại. Cờ bật Vision cho phép người dùng của demo gửi request tính phí vào project của bạn; tắt cờ và khởi động lại demo khi không sử dụng.

## Cách xử lý và giới hạn

- Dùng [`DOCUMENT_TEXT_DETECTION`](https://cloud.google.com/vision/docs/samples/vision-fulltext-detection), mỗi trang PDF hoặc frame ảnh một request. PDF render 300 DPI; không phóng lớn thêm hoặc áp dụng bộ lọc Tesseract.
- Chữ/bounding box được ghép theo dòng và ô bảng có đường kẻ, rồi ánh xạ sang schema hóa đơn. Bảng không dò được sẽ có cảnh báo; cần đối chiếu dòng hàng và số tiền trước khi lưu.
- Ảnh được gửi trực tiếp tới Google; không cần Cloud Storage bucket. Theo [giới hạn Google](https://cloud.google.com/vision/docs/supported-files), request JSON tối đa 10 MB. App giới hạn PNG ở 7 MB để chừa dung lượng base64/metadata và báo lỗi nếu vượt, không âm thầm giảm chất lượng.
- Timeout 60 giây/request, không retry tự động. Job vẫn có giới hạn tổng thời gian hiện tại. Lỗi bất kỳ trang nào làm job thất bại; người dùng quyết định đọc lại bằng engine nào.
- Chi phí/quota do Google áp dụng; xem [bảng giá](https://cloud.google.com/vision/pricing). App chỉ gửi khi người dùng chọn Vision và bấm đọc file. Kết nối lại để lấy trạng thái không gửi lại ảnh tới API.
- Healthcheck chỉ cho biết Vision được bật trong cấu hình, không bảo đảm credentials/billing/quota hợp lệ. Khi lỗi, kiểm tra API đã bật, tài khoản, quota project và billing. Thông báo gửi về UI không chứa nội dung credentials.

Mặc định vẫn có thể dùng Tesseract mà không cài SDK Google hoặc cấu hình tài khoản Google.
