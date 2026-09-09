# Receipt Reader

Ứng dụng đọc, kiểm tra và lưu hóa đơn điện tử Việt Nam. App hỗ trợ XML, PDF có lớp chữ, PDF dùng chữ vector, PDF scan và ảnh.

## Chức năng chính

- Đọc trực tiếp dữ liệu hóa đơn XML.
- Đọc bố cục và bảng PDF bằng PyMuPDF.
- OCR cục bộ bằng Tesseract cho trang không có lớp chữ sử dụng được.
- Nhận diện bảng kẻ, tách hàng hóa theo ô và ghép dữ liệu qua nhiều trang.
- Cảnh báo ô số chưa rõ, STT thiếu hoặc trùng và tổng tiền không khớp.
- Cho phép kiểm tra, sửa bản nháp rồi lưu vào SQLite hoặc SQL Server.

Chi tiết kỹ thuật của luồng PDF và OCR nằm trong [PDF_PROCESSING.md](PDF_PROCESSING.md).

## Chạy demo trên Google Colab

Tải [Receipt_Reader_Colab.ipynb](Receipt_Reader_Colab.ipynb) lên Colab và chạy các ô từ trên xuống. Notebook sẽ tạo một link `trycloudflare.com` tạm thời.

## Chạy nhanh bằng SQLite

Yêu cầu Docker Desktop đang chạy. Từ thư mục dự án:

```powershell
docker-compose -f compose.sqlite.yaml up --build -d
```

Mở [http://localhost:3000](http://localhost:3000). API health check ở [http://localhost:5000/api/health](http://localhost:5000/api/health).

Dừng app và giữ dữ liệu:

```powershell
docker-compose -f compose.sqlite.yaml down
```

## Chạy với SQL Server

Sao chép `.env.example` thành `.env`, đặt mật khẩu SQL Server, rồi chạy:

```powershell
docker-compose up --build -d
```

SQL Server được publish tại `localhost:14330`. Schema nằm trong `backend/schema.sql`.

## Cấu trúc dự án

- `backend/`: Flask API, parser hóa đơn, OCR và database repository.
- `frontend/`: giao diện React/MUI.
- `compose.sqlite.yaml`: cấu hình chạy SQLite.
- `compose.yaml`: cấu hình chạy SQL Server.
- `PDF_PROCESSING.md`: tài liệu chi tiết bộ đọc PDF.

## Lưu ý

Kết quả OCR là bản nháp và cần được đối chiếu với file gốc trước khi lưu. Các file hóa đơn `.pdf` và `.xml` được bỏ qua bởi Git để tránh đưa dữ liệu hóa đơn lên repository.
