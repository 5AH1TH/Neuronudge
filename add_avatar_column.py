import sqlite3
import os

# Correct path to your main DB
db_path = os.path.join(os.path.dirname(__file__), "instance", "db.sqlite")

if not os.path.exists(db_path):
    print(f"❌ Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE user ADD COLUMN avatar_url TEXT;")
    print("✅ Added avatar_url column to user table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ Column avatar_url already exists")
    else:
        raise
finally:
    conn.commit()
    conn.close()
