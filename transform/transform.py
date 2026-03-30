import os
import time
import logging
from datetime import datetime, timezone

import pandas as pd
from pymongo import MongoClient, UpdateOne

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI")
RAW_DB_NAME = os.getenv("MONGO_DB_NAME", "estuary_raw")
TRANSFORMED_DB_NAME = os.getenv("MONGO_TRANSFORMED_DB_NAME", "estuary_transformed")
POLL_INTERVAL = int(os.getenv("TRANSFORM_POLL_INTERVAL", "10"))


def get_dbs():
    client = MongoClient(MONGO_URI)
    return client[RAW_DB_NAME], client[TRANSFORMED_DB_NAME]


# ---------------------------------------------------------------------------
# Job 1: clean_transactions
# Mục tiêu:
#   - Validate amount > 0
#   - Flag anomaly (amount > 500 hoặc amount < 5)
#   - Standardize transaction_date thành ISO string
#   - Join product_name từ products collection
#   - Ghi ra collection txn_clean (upsert theo _id gốc)
# ---------------------------------------------------------------------------
def clean_transactions(raw_db, transformed_db):
    products = {p["product_id"]: p["name"] for p in raw_db.products.find({}, {"product_id": 1, "name": 1})}

    raw = list(raw_db.transactions.find({}))
    if not raw:
        return 0

    df = pd.DataFrame(raw)

    df = df[df["amount"] > 0].copy()
    df["is_anomaly"] = (df["amount"] > 500) | (df["amount"] < 5)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df["product_name"] = df["product_id"].map(products).fillna("unknown")

    ops = []
    for row in df.to_dict("records"):
        source_id = row.pop("_id")
        row["_source_id"] = str(source_id)
        row["_transformed_at"] = datetime.now(timezone.utc).isoformat()
        ops.append(UpdateOne({"_source_id": row["_source_id"]}, {"$set": row}, upsert=True))

    if ops:
        transformed_db.txn_clean.bulk_write(ops, ordered=False)

    log.info(f"clean_transactions: processed {len(ops)} records, {df['is_anomaly'].sum()} anomalies flagged")
    return len(ops)


# ---------------------------------------------------------------------------
# Job 2: enrich_reviews
# Mục tiêu:
#   - Join product_name từ products
#   - Normalize rating: thêm sentiment label (1-2: negative, 3: neutral, 4-5: positive)
#   - Standardize review_time
#   - Ghi ra collection reviews_enriched
# ---------------------------------------------------------------------------
def enrich_reviews(raw_db, transformed_db):
    products = {p["product_id"]: p["name"] for p in raw_db.products.find({}, {"product_id": 1, "name": 1})}

    raw = list(raw_db.reviews.find({}))
    if not raw:
        return 0

    df = pd.DataFrame(raw)

    df = df[df["rating"].between(1, 5)].copy()
    df["product_name"] = df["product_id"].map(products).fillna("unknown")
    df["sentiment"] = df["rating"].map(
        lambda r: "positive" if r >= 4 else ("negative" if r <= 2 else "neutral")
    )
    df["review_time"] = pd.to_datetime(df["review_time"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    ops = []
    for row in df.to_dict("records"):
        source_id = row.pop("_id")
        row["_source_id"] = str(source_id)
        row["_transformed_at"] = datetime.now(timezone.utc).isoformat()
        ops.append(UpdateOne({"_source_id": row["_source_id"]}, {"$set": row}, upsert=True))

    if ops:
        transformed_db.reviews_enriched.bulk_write(ops, ordered=False)

    log.info(f"enrich_reviews: processed {len(ops)} records")
    return len(ops)


# ---------------------------------------------------------------------------
# Job 3: daily_summary
# Mục tiêu:
#   - Aggregate txn_clean theo ngày + product_id
#   - Tính: total_revenue, transaction_count, avg_amount, anomaly_count
#   - Join avg_rating từ reviews_enriched
#   - Ghi ra collection daily_summary (upsert theo date + product_id)
# ---------------------------------------------------------------------------
def build_daily_summary(transformed_db):
    txn_raw = list(transformed_db.txn_clean.find({}, {"transaction_date": 1, "product_id": 1,
                                                       "product_name": 1, "amount": 1, "is_anomaly": 1}))
    rev_raw = list(transformed_db.reviews_enriched.find({}, {"product_id": 1, "rating": 1}))

    if not txn_raw:
        return 0

    txn_df = pd.DataFrame(txn_raw)
    txn_df["date"] = pd.to_datetime(txn_df["transaction_date"]).dt.date.astype(str)

    summary = (
        txn_df.groupby(["date", "product_id", "product_name"])
        .agg(
            total_revenue=("amount", "sum"),
            transaction_count=("amount", "count"),
            avg_amount=("amount", "mean"),
            anomaly_count=("is_anomaly", "sum"),
        )
        .reset_index()
    )

    if rev_raw:
        rev_df = pd.DataFrame(rev_raw)
        avg_rating = rev_df.groupby("product_id")["rating"].mean().reset_index()
        avg_rating.columns = ["product_id", "avg_rating"]
        summary = summary.merge(avg_rating, on="product_id", how="left")
    else:
        summary["avg_rating"] = None

    summary["total_revenue"] = summary["total_revenue"].round(2)
    summary["avg_amount"] = summary["avg_amount"].round(2)
    summary["avg_rating"] = summary["avg_rating"].round(2)

    # Chỉ upsert khi data thực sự thay đổi — so sánh checksum
    ops = []
    for row in summary.to_dict("records"):
        checksum = str(hash((
            row["date"], row["product_id"],
            row["total_revenue"], row["transaction_count"],
            row.get("avg_rating"),
        )))
        existing = transformed_db.daily_summary.find_one(
            {"date": row["date"], "product_id": row["product_id"]},
            {"_checksum": 1}
        )
        if existing and existing.get("_checksum") == checksum:
            continue
        row["_checksum"] = checksum
        row["_transformed_at"] = datetime.now(timezone.utc).isoformat()
        ops.append(
            UpdateOne(
                {"date": row["date"], "product_id": row["product_id"]},
                {"$set": row},
                upsert=True,
            )
        )

    if ops:
        transformed_db.daily_summary.bulk_write(ops, ordered=False)

    log.info(f"daily_summary: upserted {len(ops)} rows (skipped {len(summary) - len(ops)} unchanged)")
    return len(ops)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def run_pipeline(raw_db, transformed_db):
    log.info("--- Running transform pipeline ---")
    t1 = clean_transactions(raw_db, transformed_db)
    t2 = enrich_reviews(raw_db, transformed_db)
    t3 = build_daily_summary(transformed_db)
    log.info(f"Pipeline done: txn_clean={t1}, reviews_enriched={t2}, daily_summary={t3}")


def main():
    raw_db, transformed_db = get_dbs()
    log.info(f"Transform service connected. raw_db={RAW_DB_NAME}, transformed_db={TRANSFORMED_DB_NAME}")
    log.info(f"Poll interval: {POLL_INTERVAL}s")
    try:
        while True:
            run_pipeline(raw_db, transformed_db)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        log.info("Transform service stopped.")


if __name__ == "__main__":
    main()