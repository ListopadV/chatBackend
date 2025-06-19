from flask import Blueprint, jsonify, request
from ..models.chat import Chat
from ..models.bot import Bot
from ..models.user import User
from ..models.message import Message
from ..models.chat_message import ChatMessage
from ..schemas.chat import ChatSchema
from ..schemas.message import MessageSchema
from ..extensions import db
from ..utils.decorators import token_required
from ..utils.bot_clients import ask_gpt, ask_bard
import uuid


chat_blueprint = Blueprint('chats', __name__)
chat_schema = ChatSchema()
message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)


def choose_model(name, text, temperature, top_p, max_tokens):
    if name == 'ChatGPT':
        if text is None:
            return "Prompt is missing", 400
        response, status_code = ask_gpt(text, temperature, top_p, max_tokens)
        return response, status_code
    elif name == 'Bard':
        if text is None:
            return "Prompt is missing", 400
        response, status_code = ask_bard(text, temperature or 0.7, top_p or 0.95, max_tokens or 800)
        return response, status_code
    else:
        return "Invalid model name", 400


@chat_blueprint.route('/ask', methods=['POST'])
@token_required
def ask_model(user_id):
    data = request.json
    name = request.headers.get('X-name')
    text = data.get('text')
    chat_id = request.headers.get('X-chat-id')
    bot_id = request.headers.get('X-bot-id')
    message_order = data.get('message_order')

    if message_order is None:
        return jsonify({"message": "Message order is required"}), 400
    if text is None:
        return jsonify({"message": "You can not send an empty message"}), 400
    if chat_id is None:
        return jsonify({"message": "Unselected chat exception"}), 400
    if bot_id is None:
        return jsonify({"message": "Unselected bot exception"}), 400
    if user_id is None:
        return jsonify({"message": "Unauthorized"}), 401

    temperature = data.get('temperature')
    top_p = data.get('top_p')
    max_tokens = data.get('max_tokens')
    response_text, status_code = choose_model(name, text, temperature, top_p, max_tokens)
    if status_code != 200:
        return response_text, status_code

    try:
        message_order = int(message_order)
        u_gen = str(uuid.uuid4())
        user_msg = Message(
            message_id=u_gen,
            message_order=message_order,
            sender_type='user',
            text=text
        )
        db.session.add(user_msg)
        db.session.flush()
        chat_message_user = ChatMessage(
            message_id=u_gen,
            chat_id=chat_id
        )
        db.session.add(chat_message_user)

        b_gen = str(uuid.uuid4())
        bot_msg = Message(
            message_id=b_gen,
            message_order=message_order + 1,
            sender_type='bot',
            text=response_text
        )
        db.session.add(bot_msg)
        db.session.flush()
        chat_message_bot = ChatMessage(
            message_id=b_gen,
            chat_id=chat_id
        )
        db.session.add(chat_message_bot)
        db.session.commit()

        response = jsonify({
            "user_message": {
                "message_id": u_gen,
                "message_order": message_order,
                "sender_type": "user",
                "text": text,
                "created_at": user_msg.created_at,
            },
            "bot_message": {
                "message_id": b_gen,
                "message_order": message_order + 1,
                "sender_type": "bot",
                "text": response_text,
                "created_at": bot_msg.created_at,
            }
        })
        return response, status_code

    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/create', methods=['POST'])
@token_required
def create_chat(user_id):
    data = request.json
    name = data.get('name')
    bot_id = data.get('bot_id')
    generated = str(uuid.uuid4())

    if not all([name, bot_id]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        chat = Chat(
            chat_id=generated,
            chat_name=name,
            user_id=user_id,
            bot_id=bot_id
        )
        db.session.add(chat)
        db.session.commit()
        bot = Bot.query.filter_by(bot_id=bot_id).first()
        response = jsonify({
            "chat_id": generated,
            "chat_name": name,
            "bot_avatar": bot.bot_avatar if bot else None,
            "bot_name": bot.name if bot else None,
            "created_at": chat.created_at
        })
        return response, 200

    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/user', methods=['GET'])
@token_required
def fetch_chats(user_id):
    try:
        chats = (
            db.session.query(Chat, Bot)
            .join(Bot, Chat.bot_id == Bot.bot_id)
            .filter(Chat.user_id == user_id)
            .all()
        )
        user_chats_objects = [
            {
                "chat_id": chat.chat_id,
                "bot_id": bot.bot_id,
                "user_id": user_id,
                "chat_name": chat.chat_name,
                "bot_avatar": bot.bot_avatar,
                "bot_name": bot.name,
                "created_at": chat.created_at,
            }
            for chat, bot in chats
        ]
        response = jsonify(user_chats_objects)
        return response, 200

    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/<chatId>', methods=['GET'])
@token_required
def select_chat(user_id, chatId):
    try:
        chat = (
            db.session.query(Chat, Bot, User)
            .join(Bot, Chat.bot_id == Bot.bot_id)
            .join(User, Chat.user_id == User.user_id)
            .filter(Chat.user_id == user_id, Chat.chat_id == chatId)
            .first()
        )
        if not chat:
            return jsonify({"message": "Chat was not found"}), 400
        chat_obj, bot, user = chat
        data = {
            "chat_id": chatId,
            "user_id": user_id,
            "bot_id": bot.bot_id,
            "chat_name": chat_obj.chat_name,
            "bot_avatar": bot.bot_avatar,
            "user_avatar": user.user_avatar,
            "bot_name": bot.name
        }
        response = jsonify(data)
        return response, 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/<chatId>/delete', methods=['DELETE'])
@token_required
def delete_chat(user_id, chatId):
    try:
        chat = Chat.query.filter_by(chat_id=chatId, user_id=user_id).first()
        if not chat:
            return jsonify({"message": "Chat was not found"}), 404
        db.session.delete(chat)
        db.session.commit()
        response = jsonify({
            "message": "Chat was deleted"
        })
        return response, 200

    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500
