from ..extensions import db

class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    message_id = db.Column(db.String(36), db.ForeignKey('message.message_id'), primary_key=True)
    chat_id = db.Column(db.String(36), db.ForeignKey('chat.chat_id'), primary_key=True)
    message = db.relationship('Message', back_populates='chat_links')
    chat = db.relationship('Chat', back_populates='message_links')
