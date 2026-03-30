import os
import time
import random
import openai
from faker import Faker
from pymongo import MongoClient
from datetime import datetime

# Lấy MongoDB URI từ biến môi trường (Ví dụ: mongodb+srv://user:pass@cluster.mongodb.net/dbname)
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "estuary_demo")

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

fake = Faker()


def generate_review_text(product_name):
    try:
        sentiment = random.choices(["positive", "negative"], weights=[0.8, 0.2], k=1)[0]
        prompt = f"Write a short, detailed and realistic customer review for a product called '{product_name}' in a pet store. {sentiment.capitalize()} sentiment."

        client = openai.OpenAI()
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system",
                 "content": "You are a bot that generates realistic customer reviews for pet store products."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=100,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Error generating review:", e)
        return "Great product! My pet loves it."


def get_db_connection():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


def seed_products_if_empty(db):
    """Tạo dữ liệu sản phẩm mẫu nếu collection chưa có gì (thay thế cho init.sql)"""
    if db.products.count_documents({}) == 0:
        print("No products found. Seeding initial products...")
        initial_products = [
            {"product_id": "p001", "name": "Premium Dog Food"},
            {"product_id": "p002", "name": "Organic Catnip"},
            {"product_id": "p003", "name": "Squeaky Bone Toy"},
            {"product_id": "p004", "name": "Automatic Pet Feeder"}
        ]
        db.products.insert_many(initial_products)
        print("Seeded products.")


def get_existing_ids(db):
    products = list(db.products.find({}, {"product_id": 1, "name": 1}))
    product_ids = [p["product_id"] for p in products]
    product_names = {p["product_id"]: p["name"] for p in products}
    return product_ids, product_names


def generate_transaction(product_ids):
    product_id = random.choice(product_ids)
    transaction_time = fake.date_time_this_year()
    payment_methods = ["credit_card", "debit_card", "paypal", "crypto", "bank_transfer"]
    payment_method = random.choice(payment_methods)

    anomaly_chance = random.random()
    if anomaly_chance < 0.05:
        transaction_amount = round(random.uniform(500.0, 1000.0), 2)
    elif anomaly_chance < 0.1:
        transaction_amount = round(random.uniform(0.01, 5.0), 2)
    else:
        transaction_amount = round(random.uniform(5.0, 150.0), 2)

    return {
        "product_id": product_id,
        "amount": transaction_amount,
        "transaction_date": transaction_time,
        "payment_method": payment_method
    }


def insert_transaction(db, product_ids):
    transaction_doc = generate_transaction(product_ids)
    db.transactions.insert_one(transaction_doc)


def generate_review(product_ids, product_names):
    product_id = random.choice(product_ids)
    product_name = product_names[product_id]
    rating = random.randint(1, 5)
    review_text = generate_review_text(product_name)

    return {
        "product_id": product_id,
        "rating": rating,
        "review_text": review_text,
        "review_time": fake.date_time_this_year()
    }


def insert_review(db, product_ids, product_names):
    review_doc = generate_review(product_ids, product_names)
    db.reviews.insert_one(review_doc)


def main():
    db = get_db_connection()
    print("Connected to MongoDB!")

    seed_products_if_empty(db)

    try:
        while True:
            product_ids, product_names = get_existing_ids(db)

            if not product_ids:
                print("Waiting for products to be initialized...")
                time.sleep(2)
                continue

            action = random.choices(["insert_transaction", "insert_review"], weights=[0.6, 0.4], k=1)[0]

            if action == "insert_transaction":
                insert_transaction(db, product_ids)
                print("Inserted new transaction.")
            elif action == "insert_review":
                insert_review(db, product_ids, product_names)
                print("Inserted new review.")

            time.sleep(1)

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    finally:
        print("Data generation stopped.")


if __name__ == "__main__":
    main()