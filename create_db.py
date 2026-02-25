import sqlite3
import gspread
import json
import os
from google.oauth2.service_account import Credentials

# ===== GOOGLE AUTH =====
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

if os.environ.get("GOOGLE_CREDENTIALS"):
    credentials_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(credentials_info, scopes=scope)
else:
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)

client = gspread.authorize(creds)

sheet = client.open_by_key(
    "1wdmwIggohcNH9qVUAu5IXFxNFfVft0Qz5U-CDWIXABU"
).worksheet("Sheet9")

data = sheet.get_all_records()

# ===== SQLITE SETUP =====
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS inventory")

cursor.execute("""
CREATE TABLE inventory (
    article TEXT,
    colour TEXT,
    size TEXT,
    section TEXT,
    location TEXT,
    total INTEGER,
    value REAL,
    image TEXT
)
""")

for row in data:
    cursor.execute("""
        INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row.get("Article No"),
        row.get("Colour Name"),
        row.get("Size Name"),
        row.get("Sub Section Name"),
        row.get("Location"),
        int(row.get("Total", 0)),
        float(row.get("CBS Value at MRP", 0)),
        row.get("Image URL")
    ))

conn.commit()
conn.close()

print("✅ Database Created Successfully!")