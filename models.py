from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    telegram_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dates = db.relationship('UserDate', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'telegram_id': self.telegram_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'dates_count': len(self.dates)
        }
    
    @staticmethod
    def get_or_create(username, telegram_id=None):
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, telegram_id=telegram_id)
            db.session.add(user)
            db.session.commit()
        elif telegram_id and not user.telegram_id:
            user.telegram_id = telegram_id
            db.session.commit()
        return user


class UserDate(db.Model):
    __tablename__ = 'user_dates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    date_text = db.Column(db.String(20), nullable=True)
    event = db.Column(db.String(200), nullable=True)
    whom = db.Column(db.String(100), nullable=True)
    what_gift = db.Column(db.Text, nullable=True)
    preferences = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': f"{self.day}.{self.month}.{self.year}",
            'year': self.year,
            'month': self.month,
            'day': self.day,
            'event': self.event,
            'whom': self.whom,
            'what_gift': self.what_gift,
            'preferences': self.preferences,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def formatted_date(self):
        return f"{self.day}.{self.month}.{self.year}"


class GiftSuggestion(db.Model):
    __tablename__ = 'gift_suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_date_id = db.Column(db.Integer, db.ForeignKey('user_dates.id', ondelete='CASCADE'), nullable=False)
    suggestions = db.Column(db.Text, nullable=False)
    selected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user_date = db.relationship('UserDate', backref='gift_suggestions', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_date_id': self.user_date_id,
            'suggestions': self.suggestions,
            'selected': self.selected,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
