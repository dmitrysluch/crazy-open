#/usr/bin/python3

from models import db, InteractionType

from flask import Flask
from flask_migrate import Migrate
import os
# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crazy-open.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'Crazy open')

# Initialize SQLAlchemy and Migrate
db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    for name, descr in [
        ("Handshake", "Who has the strongest grip?!"),
        ("Kiss", "From just slightly touching lips to French kissing for the whole night, everything will work!"), 
        ("Hug", "This world is too cold and doom to miss a warm hug."),
        ("Blowjob", "Doctor prescribed me to wash my tonsils regularly."),
        ("Cuni", "I am not talking about Columbia University."),
        ("Handjob", "We need more nutting!"),
        ("Classic", "Penal-vaginal intercourse, nothing special."),
        ("Anal", "The wrong hole! I did't said stop."),
        ("Strap on", "If you want, contact https://t.me/dmitrysluch")
    ]:
        result = db.session.query(InteractionType).filter_by(name=name).one_or_none()
        if result is None:
            print("Adding interaction type:", name)
            it = InteractionType(name=name, description=descr)
            db.session.add(it)
    db.session.commit()