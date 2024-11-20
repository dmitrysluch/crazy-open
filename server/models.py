from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum

db = SQLAlchemy()

class VisibilityState(Enum):
    VISIBLE = 0
    HIDDEN = 1
    SEARCH_ONLY = 2

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    email_visibility = db.Column(SQLAlchemyEnum(VisibilityState), default=VisibilityState.SEARCH_ONLY, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    photo_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    social_links = db.relationship('SocialLink', backref='user', lazy=True)

    def is_active(self):
        return True # No bans yet
    
    def is_authenticated(self):
        return True # No bans yet
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

class SocialLink(db.Model):
    __tablename__ = 'social_links'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # e.g., "Facebook", "Instagram"
    link = db.Column(db.String(200), nullable=False)
    visibility = db.Column(SQLAlchemyEnum(VisibilityState), default=VisibilityState.SEARCH_ONLY, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class InteractionType(db.Model):
    __tablename__ = 'interaction_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, name, description):
        self.name = name
        self.description = description

class Interaction(db.Model):
    __tablename__ = 'interactions'
    id = db.Column(db.Integer, primary_key=True)
    user_1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('interaction_types.id'), nullable=False)
    details = db.Column(db.JSON, default={})
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    interaction_type = db.relationship('InteractionType', backref='interactions')

class InteractionRequest(db.Model):
    __tablename__ = 'interaction_requests'
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('interaction_types.id'), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                           onupdate=lambda: datetime.now(timezone.utc))
    interaction_type = db.relationship('InteractionType', backref='interaction_requests')
