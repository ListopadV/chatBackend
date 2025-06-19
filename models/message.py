from ..extensions import db

class Message(db.Model):
    __tablename__ = 'message'
    message_id = db.Column(db.String(36), primary_key=True, unique=True, nullable=False)
    message_order = db.Column(db.Integer, nullable=False)
    sender_type = db.Column(db.String(10), nullable=False)  # 'bot' или 'user'
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    chat_links = db.relationship('ChatMessage', back_populates='message', cascade='all, delete-orphan')
