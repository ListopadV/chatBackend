from ..extensions import db

class Chat(db.Model):
    __tablename__ = 'chat'
    chat_id = db.Column(db.String(36), primary_key=True, unique=True, nullable=False)
    chat_name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=False)
    bot_id = db.Column(db.String(36), db.ForeignKey('bot.bot_id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    user = db.relationship('User', back_populates='chats')
    bot = db.relationship('Bot', back_populates='chats')
    message_links = db.relationship('ChatMessage', back_populates='chat', cascade='all, delete-orphan')
