from gevent import monkey

monkey.patch_all()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from itsdangerous import URLSafeTimedSerializer
import os

# Import models from your models file
from models import db, User, SocialLink, InteractionType, Interaction, InteractionRequest

# Initialize Flask app
app = Flask(__name__)
app.template_folder="templates"
app.static_folder="../static"

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crazy-open.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'Crazy open')
app.config['BREVO_API_KEY'] = os.getenv('BREVO_API_KEY', 'Crazy open')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Initialize SQLAlchemy and Migrate
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


import views