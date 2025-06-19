from ..models.bot import Bot
from ..extensions import ma


class BotSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Bot
        load_instance = True
