import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "instance", "db.sqlite")

if not os.path.exists(db_path):
    print(f"❌ Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add the column only if it doesn't already exist
        cursor.execute("PRAGMA table_info(user)")
        columns = [col[1] for col in cursor.fetchall()]
        if "registered_on" not in columns:
            cursor.execute("ALTER TABLE user ADD COLUMN registered_on TEXT")
            print("✅ Column 'registered_on' added successfully.")
        else:
            print("ℹ️ Column 'registered_on' already exists.")

        conn.commit()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()