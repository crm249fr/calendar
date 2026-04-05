from database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    dates = db.relationship('UserDate', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'dates_count': len(self.dates)
        }
    
    @classmethod
    def get_or_create(cls, username):
        user = cls.query.filter_by(username=username).first()
        if not user:
            user = cls(username=username)
            db.session.add(user)
            db.session.commit()
        return user

class UserDate(db.Model):
    __tablename__ = 'user_dates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    time = db.Column(db.String(50))
    event = db.Column(db.String(200))
    whom = db.Column(db.String(100))
    what_gift = db.Column(db.Text)
    preferences = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': f"{self.day}.{self.month}.{self.year}",
            'year': self.year,
            'month': self.month,
            'day': self.day,
            'time': self.time,
            'event': self.event,
            'whom': self.whom,
            'what_gift': self.what_gift,
            'preferences': self.preferences,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_short_dict(self):
        date_str = f"{self.day}.{self.month}.{self.year}"
        if self.what_gift:
            date_str += f" (Подарок: {self.what_gift[:50]}...)"
        return date_str
