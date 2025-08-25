# make_migration.py
from Neuronudge import create_app, db
from flask_migrate import Migrate, migrate

app = create_app()
migrate_obj = Migrate(app, db)  # keep the Migrate instance

with app.app_context():
    # Call the function `migrate()` to generate migration scripts
    migrate(directory='migrations', message="Update User model (add dashboard_features)")
    print("Migration script generated.")
