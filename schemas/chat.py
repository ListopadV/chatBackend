from ..models.chat import Chat
from ..extensions import ma


class ChatSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Chat
        load_instance = True
