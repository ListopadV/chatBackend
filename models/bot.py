from ..extensions import db

class Bot(db.Model):
    __tablename__ = 'bot'
    bot_id = db.Column(db.String(36), primary_key=True, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    bot_avatar = db.Column(db.String(255))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    chats = db.relationship('Chat', back_populates='bot')
