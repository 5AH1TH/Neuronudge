# fix_user_dates.py
import os
from datetime import datetime
from Neuronudge import create_app, db
from Neuronudge.models import User

def fix_user_dates():
    app = create_app()
    with app.app_context():
        users = User.query.all()
        fixed_count = 0

        for u in users:
            changed = False

            # Fix created_at
            if isinstance(u.created_at, str):
                try:
                    u.created_at = datetime.fromisoformat(u.created_at)
                    changed = True
                except Exception as e:
                    print(f"⚠️ Could not parse created_at for {u.email}: {e}")

            elif isinstance(u.created_at, bytes):
                try:
                    u.created_at = datetime.fromisoformat(u.created_at.decode("utf-8"))
                    changed = True
                except Exception as e:
                    print(f"⚠️ Could not parse created_at for {u.email}: {e}")

            # Fix registered_on
            if isinstance(u.registered_on, str):
                try:
                    u.registered_on = datetime.fromisoformat(u.registered_on)
                    changed = True
                except Exception as e:
                    print(f"⚠️ Could not parse registered_on for {u.email}: {e}")

            elif isinstance(u.registered_on, bytes):
                try:
                    u.registered_on = datetime.fromisoformat(u.registered_on.decode("utf-8"))
                    changed = True
                except Exception as e:
                    print(f"⚠️ Could not parse registered_on for {u.email}: {e}")

            if changed:
                fixed_count += 1

        db.session.commit()
        print(f"✅ Fixed {fixed_count} user(s)")

if __name__ == "__main__":
    fix_user_dates()
