import sqlite3

conn = sqlite3.connect("database.db")
conn.execute("PRAGMA journal_mode=WAL;")
conn.commit()
conn.close()

print("WAL Mode Enabled Successfully 🚀")