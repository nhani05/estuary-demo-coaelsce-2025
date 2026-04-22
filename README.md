# 🐾 Pet Store Real-Time ETL Pipeline

Demo một **ETL pipeline hoàn chỉnh theo thời gian thực** sử dụng dữ liệu mô phỏng của một cửa hàng thú cưng. Dữ liệu được sinh tự động, transform bằng Estuary Flow, và materialized vào Supabase để hiển thị trên dashboard.

---

## 🏗 Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXTRACT                                  │
│   Data Generator (Python + Docker)                              │
│   Faker · OpenAI · 1 record/giây · 60% txn / 40% review        │
└────────────────────────┬────────────────────────────────────────┘
                         │ insert
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAW LAYER (Bronze)                           │
│   MongoDB Atlas  —  estuary_raw                                 │
│   ├── products       (seed, 4 sản phẩm)                        │
│   ├── transactions   (raw, có anomaly)                         │
│   └── reviews        (raw, rating 1–5)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │ CDC via Estuary Flow Capture
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TRANSFORM LAYER (Estuary Flow)                 │
│   Derivations bằng TypeScript                                   │
│   ├── clean-transactions.ts  → validate, flag anomaly          │
│   └── enrich-reviews.ts      → sentiment label                 │
└────────────────────────┬────────────────────────────────────────┘
                         │ Materialize
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TRANSFORMED LAYER (Silver)                      │
│   Supabase (PostgreSQL)  —  schema: estuary_raw                 │
│   ├── txn-clean          (clean · is_anomaly · product_id)     │
│   └── reviews-enriched   (sentiment · product_id · rating)     │
└─────────────────────────────────────────────────────────────────┘
```

**Latency end-to-end:** ~30–60 giây từ lúc insert vào MongoDB đến lúc dữ liệu xuất hiện tại Supabase.

---

## 📁 Cấu trúc dự án

```
project/
├── datagen/
│   ├── Dockerfile
│   ├── datagen.py                          # Data generator chính
│   └── requirements.txt
├── pet-store-flow/
│   ├── nhanlexuan05/estuary_raw/
│   │   ├── flow.yaml                       # Capture từ MongoDB + collections schema
│   │   ├── collections.yaml                # Derived collections (txn-clean, reviews-enriched)
│   │   ├── materialization.yaml            # Materialize vào Supabase
│   │   ├── source-mongodb.config.yaml      # MongoDB connection (SOPS-encrypted)
│   │   └── transforms/
│   │       ├── clean-transactions.ts       # Transform logic cho transactions
│   │       └── enrich-reviews.ts           # Transform logic cho reviews
│   └── flow_generated/typescript/          # Auto-generated TypeScript types
├── postgres/
│   └── init.sql                            # Schema khởi tạo ban đầu (tham khảo)
├── docker-compose.yml                      # Datagen + Metabase/Superset
├── collections.yaml                        # Product-stats derived collection
├── .env                                    # Biến môi trường (không commit)
└── README.md
```

---

## 🔧 Công nghệ sử dụng

| Layer | Công nghệ | Vai trò |
|---|---|---|
| Data generation | Python, Faker, OpenAI API | Sinh dữ liệu giả lập |
| Containerization | Docker, Docker Compose | Đóng gói datagen và dashboard |
| Raw storage | MongoDB Atlas (Free tier) | Bronze layer — nguồn dữ liệu gốc |
| CDC + Transform | Estuary Flow (Free tier) | Capture, derivation TypeScript, materialize |
| Clean storage | Supabase (PostgreSQL) | Silver layer — dữ liệu đã transform |
| Dashboard | Metabase hoặc Superset (Self-hosted) | Visualization |

Tất cả công nghệ đều **miễn phí** ở mức độ sử dụng của demo này.

---

## ⚙️ Yêu cầu hệ thống

- [Docker Desktop](https://docs.docker.com/get-docker/) đã cài đặt và đang chạy
- Tài khoản [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (Free tier)
- Tài khoản [Estuary Flow](https://dashboard.estuary.dev/) (Free tier)
- Tài khoản [Supabase](https://supabase.com/) (Free tier)
- (Tùy chọn) OpenAI API Key — nếu không có, script vẫn chạy với review mặc định

---

## 🚀 Hướng dẫn cài đặt & chạy

### Bước 1: Cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc:

```env
# MongoDB Atlas connection string
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.xxxxxx.mongodb.net/?retryWrites=true&w=majority

# Tên database
MONGO_DB_NAME=estuary_raw

# OpenAI (tùy chọn)
OPENAI_API_KEY=sk-your-key-here
```

### Bước 2: Khởi chạy Data Generator

```bash
docker-compose up --build -d datagen
```

Container `mongodb-cloud-datagen` sẽ liên tục sinh transactions và reviews vào `estuary_raw` trên MongoDB Atlas (1 record/giây).

Kiểm tra logs:

```bash
docker logs -f mongodb-cloud-datagen
```

Output mẫu:
```
Connected to MongoDB!
Inserted new transaction.
Inserted new review.
Inserted new transaction.
```

### Bước 3: Thiết lập Estuary Flow

#### 3a. Tạo Capture từ MongoDB

1. Đăng nhập [dashboard.estuary.dev](https://dashboard.estuary.dev)
2. **Captures → New Capture → MongoDB**
3. Điền connection string MongoDB Atlas, chọn database `estuary_raw`
4. Chọn 3 collections: `products`, `transactions`, `reviews`
5. Publish capture — Estuary sẽ bắt đầu stream CDC từ MongoDB

#### 3b. Deploy Derivations

Các transform logic nằm trong `pet-store-flow/nhanlexuan05/estuary_raw/transforms/`:

- `clean-transactions.ts` — loại bỏ amount ≤ 0, flag anomaly (`amount > 500` hoặc `< 5`), chuẩn hóa timestamp
- `enrich-reviews.ts` — validate rating [1–5], gán sentiment (`positive` ≥ 4, `neutral` = 3, `negative` ≤ 2)

Deploy bằng Estuary CLI:

```bash
cd pet-store-flow
flowctl catalog publish --source nhanlexuan05/flow.yaml
```

#### 3c. Thiết lập Materialization vào Supabase

Cấu hình trong `materialization.yaml` đã trỏ đến Supabase. Cập nhật credentials Supabase của bạn:

```yaml
# pet-store-flow/nhanlexuan05/estuary_raw/materialization.yaml
endpoint:
  connector:
    config:
      address: <your-project>.supabase.co:5432
      database: postgres
      user: postgres
      password: <your-password>
      schema: estuary_raw
```

Publish materialization:

```bash
flowctl catalog publish --source nhanlexuan05/estuary_raw/materialization.yaml
```

Sau khi publish, Estuary tự động tạo bảng `txn-clean` và `reviews-enriched` trong Supabase schema `estuary_raw`.

### Bước 4: Khởi chạy Dashboard

```bash
# Metabase (port 3000)
docker-compose up -d metabase

# Hoặc Superset (port 8088)
docker-compose up -d superset
```

Kết nối Metabase/Superset với Supabase PostgreSQL:

```
Host:     db.<project-ref>.supabase.co
Port:     5432
Database: postgres
Schema:   estuary_raw
User:     postgres
Password: <your-password>
```

Tạo dashboard với các charts từ `txn-clean` và `reviews-enriched`.

---

## 📊 Transform Derivations

### `clean-transactions.ts`

Đọc từ `estuary_raw/transactions`, ghi vào `estuary_raw/txn-clean`.

| Bước | Logic |
|---|---|
| Filter | Loại bỏ records có `amount <= 0` |
| Anomaly | Flag `is_anomaly = true` nếu `amount > 500` hoặc `amount < 5` |
| Timestamp | Chuẩn hóa `transaction_date` sang ISO 8601 |
| Key | `id` lấy từ MongoDB `_id.$oid` |

### `enrich-reviews.ts`

Đọc từ `estuary_raw/reviews`, ghi vào `estuary_raw/reviews-enriched`.

| Bước | Logic |
|---|---|
| Validate | Loại bỏ records có `rating` ngoài khoảng [1, 5] |
| Sentiment | `positive` (≥ 4) · `neutral` (3) · `negative` (≤ 2) |
| Timestamp | Chuẩn hóa `review_time` sang ISO 8601 |
| Key | `id` lấy từ MongoDB `_id.$oid` |

---

## 🧹 Dọn dẹp

```bash
# Dừng containers
docker-compose down

# Dừng và xóa volumes
docker-compose down -v
```

Vào Estuary Flow dashboard → Pause Capture và Materialization để tránh tốn quota.

---

## 📈 Hướng phát triển tiếp theo

- **Product-stats derived collection** — `collections.yaml` ở root đã định nghĩa collection tổng hợp revenue, rating, sentiment theo `product_id` — có thể deploy để có thêm một layer Gold
- **Anomaly alerts** — `anomaly-alerts` derivation đã được scaffold trong `flow_generated/`, cần implement logic và publish
- **Incremental watermark** — thêm state vào derivation để chỉ xử lý records mới
- **Observability** — tích hợp Estuary metrics với alerting khi pipeline lag hoặc error rate tăng
- **Machine Learning** — dùng `reviews-enriched` để train sentiment classifier thay cho rule-based hiện tại