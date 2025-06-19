from ..extensions import db

class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.String(36), primary_key=True, unique=True, nullable=False)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    user_avatar = db.Column(db.Text, default='pohuy 2')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    chats = db.relationship('Chat', back_populates='user')
