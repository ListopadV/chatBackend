from flask import Blueprint, jsonify, request
from ..models.message import Message
from ..models.chat import Chat
from ..models.bot import Bot
from ..models.chat_message import ChatMessage
from ..schemas.message import MessageSchema
from ..extensions import db
from ..utils.decorators import token_required

messages_blueprint = Blueprint('messages', __name__)
messages_schema = MessageSchema(many=True)


@messages_blueprint.route('/fetch', methods=['GET'])
@token_required
def get_messages(user_id):
    chat_id = request.headers.get('X-chat-id')
    bot_id = request.headers.get('X-bot-id')

    if not chat_id:
        return jsonify({"message": "Unselected chat exception"}), 400
    if not bot_id:
        return jsonify({"message": "Unselected bot exception"}), 400

    try:
        chat = Chat.query.filter_by(chat_id=chat_id, bot_id=bot_id, user_id=user_id).first()
        if not chat:
            return jsonify({"message": "Chat not found"}), 404

        messages = (
            db.session.query(Message)
            .join(ChatMessage, Message.message_id == ChatMessage.message_id)
            .filter(ChatMessage.chat_id == chat_id)
            .order_by(Message.message_order.asc())
            .all()
        )

        bot = Bot.query.filter_by(bot_id=bot_id).first()
        bot_avatar = bot.bot_avatar if bot and bot.bot_avatar else "no avatar"
        user_avatar = "no ava"

        message_objects = [
            {
                "message_id": m.message_id,
                "message_order": m.message_order,
                "sender_type": m.sender_type,
                "text": m.text,
                "created_at": m.created_at,
                "avatar": bot_avatar if m.sender_type == 'bot' else user_avatar
            }
            for m in messages if m.sender_type in ['bot', 'user']
        ]

        response = jsonify({"messages": message_objects})
        return response, 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500
