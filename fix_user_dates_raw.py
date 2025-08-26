# fix_user_dates_raw.py
from datetime import datetime
from Neuronudge import create_app, db

def safe_parse(value):
    """Try to parse string/bytes into datetime, fallback to utcnow."""
    if not value:
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.split(".")[0], fmt)
            except Exception:
                continue
    # fallback
    return datetime.utcnow()

def fix_user_dates_raw():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        result = conn.execute(db.text("SELECT id, created_at, registered_on FROM user"))
        rows = result.fetchall()

        fixed_count = 0
        for row in rows:
            user_id = row[0]
            created_at = safe_parse(row[1])
            registered_on = safe_parse(row[2])

            conn.execute(
                db.text("UPDATE user SET created_at = :ca, registered_on = :ro WHERE id = :id"),
                {"ca": created_at, "ro": registered_on, "id": user_id}
            )
            fixed_count += 1

        conn.commit()
        print(f"✅ Fixed {fixed_count} users")

if __name__ == "__main__":
    fix_user_dates_raw()
