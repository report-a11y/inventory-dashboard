import os
from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# ----------------------------
# AUTO CREATE TEMPLATE FILE
# ----------------------------

if not os.path.exists("templates"):
    os.makedirs("templates")

if not os.path.exists("templates/index.html"):
    with open("templates/index.html", "w", encoding="utf-8") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Inventory Dashboard</title>
</head>
<body>
    <h1>Inventory Dashboard Working ✅</h1>
    <h2>Total Stock: {{ total_stock }}</h2>
    <h2>Total Value: ₹ {{ total_value }}</h2>
</body>
</html>
""")

# ----------------------------
# GOOGLE SHEET CONNECTION
# ----------------------------

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


@app.route("/")
def index():
    data = sheet.get_all_records()

    total_stock = sum(int(d["Total"]) for d in data)
    total_value = sum(float(d["CBS Value at MRP"]) for d in data)

    return render_template(
        "index.html",
        total_stock=total_stock,
        total_value=total_value
    )


if __name__ == "__main__":
    app.run(debug=True)
