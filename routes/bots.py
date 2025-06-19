from flask import Blueprint, request, jsonify
from ..models.bot import Bot
from ..schemas.bot import BotSchema
from ..extensions import db
from ..utils.decorators import token_required
import uuid


bots_blueprint = Blueprint('bots', __name__)
bot_schema = BotSchema()
bots_schema = BotSchema(many=True)


@bots_blueprint.route('/create', methods=['POST'])
@token_required
def create_bot(user_id):
    data = request.json
    name = data.get('name')
    model = data.get('model')
    avatar = data.get('avatar')
    description = data.get('description')
    generated = str(uuid.uuid4())

    if not all([name, model]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        bot = Bot(
            bot_id=generated,
            name=name,
            model=model,
            bot_avatar=avatar,
            description=description
        )
        db.session.add(bot)
        db.session.commit()

        response = jsonify({
            "bot_id": bot.bot_id,
            "name": bot.name,
            "model": bot.model,
            "bot_avatar": bot.bot_avatar
        })
        return response, 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@bots_blueprint.route('/bots', methods=['GET'])
@token_required
def get_bots(user_id):
    try:
        bots = Bot.query.all()
        if not bots:
            return jsonify({"message": "No bots were found"}), 200

        info_objects = bots_schema.dump(bots)
        response = jsonify({"bots": info_objects})
        return response, 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500
