import os
import json
from flask import Flask, render_template, request, jsonify
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# Google API Scope
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ✅ DUAL MODE AUTH (Local + Render)
if os.environ.get("GOOGLE_CREDENTIALS"):
    # 🔥 Render Environment
    credentials_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        credentials_info,
        scopes=scope
    )
else:
    # 🔥 Local File Method
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=scope
    )

client = gspread.authorize(creds)

sheet = client.open_by_key(
    "1wdmwIggohcNH9qVUAu5IXFxNFfVft0Qz5U-CDWIXABU"
).worksheet("Sheet9")


def get_data():
    return sheet.get_all_records()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/filter")
def filter_data():
    data = get_data()

    article = request.args.get("article", "")
    colour = request.args.get("colour", "")
    size = request.args.get("size", "")
    section = request.args.get("section", "")
    location = request.args.get("location", "")
    search = request.args.get("search", "")

    # 🔍 Filters
    if article:
        data = [d for d in data if d.get("Article No") == article]

    if colour:
        data = [d for d in data if d.get("Colour Name") == colour]

    if size:
        data = [d for d in data if d.get("Size Name") == size]

    if section:
        data = [d for d in data if d.get("Sub Section Name") == section]

    if location:
        data = [d for d in data if d.get("Location") == location]

    if search:
        data = [d for d in data if search.lower() in str(d).lower()]

    # 📊 Summary
    total_stock = sum(int(d.get("Total", 0)) for d in data)
    total_value = sum(float(d.get("CBS Value at MRP", 0)) for d in data)

    category_summary = {}
    size_summary = {}

    for d in data:
        category = d.get("Sub Section Name", "")
        size_name = d.get("Size Name", "")
        qty = int(d.get("Total", 0))

        category_summary[category] = category_summary.get(category, 0) + qty
        size_summary[size_name] = size_summary.get(size_name, 0) + qty

    all_data = get_data()

    return jsonify({
        "data": data,
        "total_stock": total_stock,
        "total_value": total_value,
        "total_articles": len(data),
        "category_summary": category_summary,
        "size_summary": size_summary,
        "articles": sorted(set(d.get("Article No") for d in all_data if d.get("Article No"))),
        "colours": sorted(set(d.get("Colour Name") for d in all_data if d.get("Colour Name"))),
        "sizes": sorted(set(d.get("Size Name") for d in all_data if d.get("Size Name"))),
        "sections": sorted(set(d.get("Sub Section Name") for d in all_data if d.get("Sub Section Name"))),
        "locations": sorted(set(d.get("Location") for d in all_data if d.get("Location"))),
    })


if __name__ == "__main__":
    app.run(debug=True)