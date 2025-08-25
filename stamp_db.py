# stamp_db.py
from Neuronudge import create_app, db
from flask_migrate import Migrate, stamp

app = create_app()
migrate = Migrate(app, db)

with app.app_context():
    stamp(directory='migrations', revision='head')
    print("Database stamped to latest revision.")
