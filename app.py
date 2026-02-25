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

# ---------------- DB ---------------- #

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- GOOGLE SYNC ---------------- #

def sync_from_google():

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
            records = sheet.get_all_records()

            conn = sqlite3.connect(DB_NAME, timeout=10)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM inventory")

            for row in records:

                total = row.get("Total")
                value = row.get("CBS Value at MRP")

                total = int(total) if str(total).strip().isdigit() else 0

                try:
                    value = float(value)
                except:
                    value = 0

                # ---------- FIX IMAGE HERE ----------
                image_url = row.get("Image URL")

                if image_url and "drive.google.com" in image_url:

                    if "id=" in image_url:
                        file_id = image_url.split("id=")[-1]

                    elif "/d/" in image_url:
                        file_id = image_url.split("/d/")[1].split("/")[0]

                    else:
                        file_id = None

                    if file_id:
                        image_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"

                # ------------------------------------

                cursor.execute("""
                    INSERT INTO inventory
                    (article, colour, size, section, location, total, value, image)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get("Article No"),
                    row.get("Colour Name"),
                    row.get("Size Name"),
                    row.get("Sub Section Name"),
                    row.get("Location"),
                    total,
                    value,
                    image_url
                ))

            conn.commit()
            conn.close()

            print("Synced Successfully ✅")
            socketio.emit("data_updated")

        except Exception as e:
            print("Sync Error:", e)

        time.sleep(20)


# ---------------- ROUTES ---------------- #

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/filter")
def filter_data():

    page = int(request.args.get("page", 1))
    per_page = 50
    offset = (page - 1) * per_page

    article = request.args.get("article")
    colour = request.args.get("colour")
    size = request.args.get("size")
    section = request.args.get("section")
    location = request.args.get("location")
    search = request.args.get("search")

    conn = get_db_connection()
    cursor = conn.cursor()

    base_query = "FROM inventory WHERE 1=1"
    params = []

    if article:
        base_query += " AND article=?"
        params.append(article)

    if colour:
        base_query += " AND colour=?"
        params.append(colour)

    if size:
        base_query += " AND size=?"
        params.append(size)

    if section:
        base_query += " AND section=?"
        params.append(section)

    if location:
        base_query += " AND location=?"
        params.append(location)

    if search:
        base_query += """ AND (
            article LIKE ? OR
            colour LIKE ? OR
            size LIKE ? OR
            section LIKE ? OR
            location LIKE ?
        )"""
        for _ in range(5):
            params.append(f"%{search}%")

    # -------- MAIN DATA -------- #
    cursor.execute("SELECT * " + base_query + " ORDER BY article ASC LIMIT ? OFFSET ?", params + [per_page, offset])
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]

    # -------- SUMMARY -------- #
    cursor.execute("SELECT SUM(total), SUM(value) " + base_query, params)
    summary = cursor.fetchone()

    total_stock = summary[0] or 0
    total_value = summary[1] or 0

    # -------- CATEGORY SUMMARY -------- #
    cursor.execute("SELECT section, SUM(total) " + base_query + " GROUP BY section", params)
    category_summary = {row[0]: row[1] for row in cursor.fetchall() if row[0]}

    # -------- SIZE SUMMARY -------- #
    cursor.execute("SELECT size, SUM(total) " + base_query + " GROUP BY size", params)
    size_summary = {row[0]: row[1] for row in cursor.fetchall() if row[0]}

    # -------- DROPDOWN DATA -------- #
    cursor.execute("SELECT DISTINCT article FROM inventory")
    articles = sorted([row[0] for row in cursor.fetchall() if row[0]])

    cursor.execute("SELECT DISTINCT colour FROM inventory")
    colours = sorted([row[0] for row in cursor.fetchall() if row[0]])

    cursor.execute("SELECT DISTINCT size FROM inventory")
    sizes = sorted([row[0] for row in cursor.fetchall() if row[0]])

    cursor.execute("SELECT DISTINCT section FROM inventory")
    sections = sorted([row[0] for row in cursor.fetchall() if row[0]])

    cursor.execute("SELECT DISTINCT location FROM inventory")
    locations = sorted([row[0] for row in cursor.fetchall() if row[0]])

    # -------- TOTAL COUNT FOR PAGINATION -------- #
    cursor.execute("SELECT COUNT(*) " + base_query, params)
    total_rows = cursor.fetchone()[0]
    total_pages = (total_rows // per_page) + (1 if total_rows % per_page else 0)

    conn.close()

    return jsonify({
        "data": data,
        "total_stock": total_stock,
        "total_value": total_value,
        "total_articles": len(data),
        "category_summary": category_summary,
        "size_summary": size_summary,
        "articles": articles,
        "colours": colours,
        "sizes": sizes,
        "sections": sections,
        "locations": locations,
        "page": page,
        "total_pages": total_pages,
    })


# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    threading.Thread(target=sync_from_google, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=10000)