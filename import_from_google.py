import sqlite3
import gspread
from google.oauth2.service_account import Credentials
import os

# -------- GOOGLE AUTH --------
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

records = sheet.get_all_records()

# -------- SQLITE --------
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Optional: clear old data
cursor.execute("DELETE FROM inventory")

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
    row.get("Total"),
    row.get("CBS Value at MRP"),
    image_url   # 👈 YAHAN AB NEW URL JAYEGA
))

conn.commit()
conn.close()

print("Google Sheet Data Imported Successfully 🚀")