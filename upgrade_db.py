# upgrade_db.py
from Neuronudge import create_app, db
from flask_migrate import Migrate, upgrade

app = create_app()
migrate = Migrate(app, db)

with app.app_context():
    upgrade(directory='migrations')
    print("Database upgraded to latest revision.")
