import sqlite3
import threading
import time
import gspread
from google.oauth2.service_account import Credentials
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_NAME = "database.db"

# 🔥 IN-MEMORY CACHE (Ultra Fast Mode)
inventory_cache = []
category_cache = {}
size_cache = {}
summary_cache = {}

# ---------------- DB ---------------- #

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- GOOGLE SYNC ---------------- #

def sync_from_google():
    global inventory_cache, category_cache, size_cache, summary_cache

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=scope
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_key(
        "1wdmwIggohcNH9qVUAu5IXFxNFfVft0Qz5U-CDWIXABU"
    ).worksheet("Sheet9")

    while True:
        try:
            print("🚀 Sync Started")
            records = sheet.get_all_records()
            print("🔥 RECORDS LENGTH:", len(records))

            new_data = []
            category = {}
            size = {}
            total_stock = 0
            total_value = 0

            for row in records:
                total = int(row.get("Total") or 0)

                try:
                    value = float(row.get("CBS Value at MRP") or 0)
                except:
                    value = 0

                item = {
                    "article": row.get("Article No"),
                    "colour": row.get("Colour Name"),
                    "size": row.get("Size Name"),
                    "section": row.get("Sub Section Name"),
                    "location": row.get("Location"),
                    "total": total,
                    "value": value,
                    "image": row.get("Image URL")
                }

                new_data.append(item)

                total_stock += total
                total_value += value

                if item["section"]:
                    category[item["section"]] = category.get(item["section"], 0) + total

                if item["size"]:
                    size[item["size"]] = size.get(item["size"], 0) + total

            inventory_cache = new_data
            category_cache = category
            size_cache = size
            summary_cache = {
                "total_stock": total_stock,
                "total_value": total_value
            }

            print("⚡ Cache Updated:", len(new_data), "items")
            socketio.emit("data_updated")

        except Exception as e:
            print("Sync Error:", e)

        time.sleep(120)
# ---------------- ROUTES ---------------- #

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/filter")
def filter_data():
    search = request.args.get("search", "").lower()
    article = request.args.get("article")
    colour = request.args.get("colour")
    size = request.args.get("size")
    section = request.args.get("section")
    location = request.args.get("location")

    filtered = inventory_cache

    if search:
        filtered = [i for i in filtered if search in str(i).lower()]
    if article:
        filtered = [i for i in filtered if i["article"] == article]
    if colour:
        filtered = [i for i in filtered if i["colour"] == colour]
    if size:
        filtered = [i for i in filtered if i["size"] == size]
    if section:
        filtered = [i for i in filtered if i["section"] == section]
    if location:
        filtered = [i for i in filtered if i["location"] == location]

    return jsonify({
        "data": filtered[:20],  # pagination
        "total_stock": summary_cache.get("total_stock", 0),
        "total_value": summary_cache.get("total_value", 0),
        "total_articles": len(filtered),
        "category_summary": category_cache,
        "size_summary": size_cache
    })

# ---------------- MAIN ---------------- #
# Start background sync always
threading.Thread(target=sync_from_google, daemon=True).start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
