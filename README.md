# 🐾 Pet Store Real-Time ETL Pipeline

Dự án demo một **ETL pipeline hoàn chỉnh theo thời gian thực** sử dụng dữ liệu mô phỏng của một cửa hàng thú cưng. Dữ liệu được sinh tự động, làm sạch, transform, và hiển thị trên dashboard — hoàn toàn tự động và liên tục.

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
                         │ poll mỗi 10 giây
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TRANSFORM LAYER                              │
│   Transform Container (Python + pandas + Docker)               │
│   ├── clean_transactions  → validate, flag anomaly, join name  │
│   ├── enrich_reviews      → sentiment label, join product name │
│   └── daily_summary       → aggregate revenue + checksum guard │
└────────────────────────┬────────────────────────────────────────┘
                         │ upsert (idempotent)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TRANSFORMED LAYER (Silver/Gold)                 │
│   MongoDB Atlas  —  estuary_transformed                         │
│   ├── txn_clean          (clean · is_anomaly · product_name)   │
│   ├── reviews_enriched   (sentiment · product_name)            │
│   └── daily_summary      (revenue · avg_rating · anomaly_count)│
└────────────────────────┬────────────────────────────────────────┘
                         │ CDC (Change Data Capture)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LOAD LAYER                                   │
│   Estuary Flow  →  Capture + Materialize                       │
│                         │                                       │
│                         ▼                                       │
│   Metabase Dashboard (localhost:3000)                          │
│   ├── Doanh thu theo ngày                                      │
│   ├── Top sản phẩm theo doanh thu                              │
│   ├── Sentiment reviews                                        │
│   └── Anomaly transactions                                     │
└─────────────────────────────────────────────────────────────────┘
```

**Latency end-to-end:** ~75 giây từ lúc insert đến lúc thấy trên dashboard.

---

## 📁 Cấu trúc dự án

```
project/
├── datagen/
│   ├── Dockerfile
│   ├── datagen.py          # Data generator chính
│   └── requirements.txt
├── transform/
│   ├── Dockerfile
│   ├── transform.py        # 3 transform jobs
│   └── requirements.txt
├── docker-compose.yml      # Orchestrate tất cả containers
├── .env                    # Biến môi trường (không commit)
└── README.md
```

---

## 🔧 Công nghệ sử dụng

| Layer | Công nghệ | Vai trò |
|---|---|---|
| Data generation | Python, Faker, OpenAI API | Sinh dữ liệu giả lập |
| Containerization | Docker, Docker Compose | Đóng gói và orchestrate |
| Raw storage | MongoDB Atlas (Free tier) | Bronze layer |
| Transformation | Python, pandas | ETL transform jobs |
| Clean storage | MongoDB Atlas | Silver/Gold layer |
| CDC streaming | Estuary Flow (Free tier) | Capture & Materialize |
| Dashboard | Metabase (Self-hosted) | Visualization |

Tất cả công nghệ đều **miễn phí** ở mức độ sử dụng của demo này.

---

## ⚙️ Yêu cầu hệ thống

- [Docker Desktop](https://docs.docker.com/get-docker/) đã cài đặt và đang chạy
- Tài khoản [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (Free tier)
- Tài khoản [Estuary Flow](https://dashboard.estuary.dev/) (Free tier)
- (Tùy chọn) OpenAI API Key — nếu không có, script vẫn chạy với review mặc định

---

## 🚀 Hướng dẫn cài đặt & chạy

### Bước 1: Clone dự án và cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc:

```env
# MongoDB Atlas connection string
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.xxxxxx.mongodb.net/?retryWrites=true&w=majority

# Tên database
MONGO_DB_NAME=estuary_raw
MONGO_TRANSFORMED_DB_NAME=estuary_transformed

# Số giây giữa mỗi lần transform (mặc định 10)
TRANSFORM_POLL_INTERVAL=10

# OpenAI (tùy chọn)
OPENAI_API_KEY=sk-your-key-here
```

### Bước 2: Khởi chạy toàn bộ pipeline

```bash
docker-compose up --build -d
```

Lệnh này sẽ khởi động 3 containers:
- `mongodb-cloud-datagen` — liên tục sinh dữ liệu vào `estuary_raw`
- `mongodb-cloud-transform` — poll và transform sang `estuary_transformed` mỗi 10 giây
- `metabase` — dashboard tại `http://localhost:3000`

### Bước 3: Kiểm tra logs

```bash
# Xem datagen đang chạy
docker logs -f mongodb-cloud-datagen

# Xem transform pipeline
docker logs -f mongodb-cloud-transform
```

Output transform sẽ như sau:
```
2026-03-30 [INFO] --- Running transform pipeline ---
2026-03-30 [INFO] clean_transactions: processed 142 records, 8 anomalies flagged
2026-03-30 [INFO] enrich_reviews: processed 89 records
2026-03-30 [INFO] daily_summary: upserted 4 rows (skipped 8 unchanged)
```

### Bước 4: Thiết lập Estuary Flow

1. Đăng nhập [dashboard.estuary.dev](https://dashboard.estuary.dev)
2. **Captures** → **New Capture** → chọn **MongoDB**
3. Điền `MONGO_URI`, chọn database `estuary_transformed`, chọn 3 collections: `txn_clean`, `reviews_enriched`, `daily_summary`
4. **Materializations** → **New Materialization** → chọn destination (Google Sheets hoặc khác)

### Bước 5: Thiết lập Metabase Dashboard

1. Mở `http://localhost:3000`
2. Tạo tài khoản admin
3. Kết nối MongoDB với connection string:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxxx.mongodb.net/estuary_transformed?retryWrites=true&w=majority
   ```
4. Tạo dashboard với các charts từ 3 collections đã transform
5. Bật auto-refresh 1 phút: icon đồng hồ → **1 minute**

---

## 📊 Transform jobs

### `clean_transactions`
Đọc từ `estuary_raw.transactions`, ghi vào `estuary_transformed.txn_clean`.

- Loại bỏ records có `amount <= 0`
- Flag anomaly: `amount > 500` hoặc `amount < 5`
- Join `product_name` từ `products`
- Standardize `transaction_date` sang ISO 8601
- Upsert idempotent theo `_source_id`

### `enrich_reviews`
Đọc từ `estuary_raw.reviews`, ghi vào `estuary_transformed.reviews_enriched`.

- Validate `rating` trong khoảng [1, 5]
- Thêm `sentiment`: `positive` (≥4), `neutral` (3), `negative` (≤2)
- Join `product_name` từ `products`
- Standardize `review_time` sang ISO 8601

### `daily_summary`
Đọc từ `estuary_transformed.txn_clean` + `reviews_enriched`, ghi vào `estuary_transformed.daily_summary`.

- Aggregate theo `date` + `product_id`
- Tính: `total_revenue`, `transaction_count`, `avg_amount`, `anomaly_count`
- Join `avg_rating` từ reviews
- Checksum guard: chỉ upsert khi data thực sự thay đổi, tránh write amplification cho Estuary CDC

---

## 🧹 Dọn dẹp

```bash
# Dừng tất cả containers
docker-compose down

# Dừng và xóa cả volumes (xóa Metabase data)
docker-compose down -v
```

Sau khi dừng Docker, vào Estuary Flow → Pause Capture và Materialization để tiết kiệm tài nguyên.

---

## 📈 Hướng phát triển tiếp theo

- **Incremental processing** — thêm watermark để transform chỉ xử lý records mới thay vì toàn bộ collection
- **Observability** — thêm alerting khi pipeline crash hoặc throughput bất thường
- **Schema validation** — thêm contract giữa datagen và transform
- **Machine Learning** — dùng `reviews_enriched` để train sentiment classifier, dùng `txn_clean` để build anomaly detection model