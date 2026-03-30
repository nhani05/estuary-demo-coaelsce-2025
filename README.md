# 🚀 Estuary Real-Time CDC Demo: MongoDB to Google Sheets

Dự án này là một bản demo trực quan về luồng dữ liệu theo thời gian thực (Real-time Change Data Capture - CDC) sử dụng **Estuary Flow**. Dữ liệu mua hàng và đánh giá sản phẩm giả lập sẽ được tạo liên tục, lưu trữ trên MongoDB Atlas, và tự động đồng bộ sang Google Sheets thông qua Estuary.

## 🏗 Kiến trúc dự án (Architecture)

1. **Nguồn phát sinh dữ liệu (Data Generator):** Một script Python được đóng gói bằng Docker. Script này sử dụng thư viện `Faker` và `OpenAI API` để liên tục tạo ra các giao dịch (transactions) và đánh giá (reviews) giả lập, sau đó đẩy thẳng lên MongoDB.
2. **Cơ sở dữ liệu nguồn (Source Database):** **MongoDB Cloud (Atlas)** đóng vai trò lưu trữ dữ liệu gốc.
3. **Động cơ CDC (Streaming Engine):** **Estuary Flow** sẽ kết nối với MongoDB để "lắng nghe" các thay đổi dữ liệu (Capture) theo thời gian thực.
4. **Đích đến (Destination):** Estuary Flow tự động đẩy dữ liệu nhận được sang **Google Sheets** (Materialization) để dễ dàng quan sát mà không cần viết SQL.

---

## 📋 Yêu cầu hệ thống (Prerequisites)

Để chạy được dự án này, bạn cần chuẩn bị:
- Đã cài đặt [Docker](https://docs.docker.com/get-docker/) và [Docker Compose](https://docs.docker.com/compose/install/).
- Một tài khoản/Cluster **MongoDB Atlas** miễn phí (đã lấy được chuỗi kết nối `MONGO_URI`).
- Một tài khoản [Estuary Flow](https://dashboard.estuary.dev/).
- (Tùy chọn) API Key của OpenAI để sinh nội dung review phong phú hơn.

---

## ⚙️ Hướng dẫn cài đặt & Khởi chạy (Setup & Run)

### Bước 1: Cấu hình biến môi trường
Tạo một file có tên `.env` nằm ở thư mục gốc của dự án (cùng cấp với file `docker-compose.yml`) và điền các thông tin sau:

```env
# Chuỗi kết nối MongoDB Atlas của bạn
MONGO_URI=mongodb+srv://<username>:<password>@<cluster-url>.mongodb.net/?retryWrites=true&w=majority

# Tên database muốn lưu trữ
MONGO_DB_NAME=estuary_demo

# OpenAI API Key (nếu có, nếu không API sẽ báo lỗi 429 nhưng script vẫn chạy dùng dữ liệu mặc định)
OPENAI_API_KEY=sk-your-openai-api-key
```

### Bước 2: Khởi chạy Data Generator
Mở terminal, trỏ tới thư mục chứa dự án và chạy lệnh sau để build và khởi động script Python ngầm bằng Docker:

```bash
docker-compose up --build -d
```

Để kiểm tra xem script có đang hoạt động tốt và đang đẩy dữ liệu lên MongoDB hay không, xem log bằng lệnh:
```bash
docker logs -f mongodb-cloud-datagen
```
*(Nhấn `Ctrl + C` để thoát màn hình log)*

### Bước 3: Thiết lập Pipeline trên Estuary Flow

1. **Tạo Capture (Hút dữ liệu):**
   - Đăng nhập Estuary Flow > **Captures** > **New Capture**.
   - Chọn connector **MongoDB**.
   - Điền `MONGO_URI` của bạn vào phần cấu hình kết nối.
   - Nhấn **Next**, chọn các collections (`products`, `transactions`, `reviews`) và **Save and Publish**.

2. **Tạo Materialization (Đổ dữ liệu):**
   - Tạo một file **Google Sheets** trống và copy đường link URL.
   - Trên Estuary Flow > **Materializations** > **New Materialization**.
   - Chọn connector **Google Sheets**.
   - Xác thực tài khoản Google và dán đường link URL vào.
   - Chọn Capture MongoDB vừa tạo làm Source Collections.
   - Nhấn **Next** > **Save and Publish**.

### Bước 4: Quan sát kết quả
Mở file Google Sheets của bạn ra. Bạn sẽ thấy các tab mới (`transactions`, `reviews`) tự động xuất hiện và dữ liệu liên tục được cập nhật theo thời gian thực mỗi khi script Python sinh ra dữ liệu mới trên MongoDB.

---

## 🧹 Dọn dẹp hệ thống (Teardown)

Khi đã chạy xong demo và muốn tắt máy phát dữ liệu, hãy chạy lệnh sau trong terminal:

```bash
docker-compose down
```
Lệnh này sẽ dừng và xóa container chạy ngầm, ngừng việc đẩy dữ liệu rác lên MongoDB của bạn. Đừng quên tạm dừng (Pause) Capture và Materialization trên giao diện Estuary Flow để tiết kiệm tài nguyên hệ thống.
```
