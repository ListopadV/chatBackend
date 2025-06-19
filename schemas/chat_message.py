from ..models.chat_message import ChatMessage
from ..extensions import ma


class ChatMessageSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ChatMessage
        load_instance = True
