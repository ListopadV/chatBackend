from flask import Blueprint, jsonify, request
from configuration import token_required, ask_bard, ask_gpt, connection_pool
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

chat_blueprint = Blueprint('chats', __name__)


def get_db_connection():
    return connection_pool.getconn()


def release_db_connection(connection):
    if connection:
        connection_pool.putconn(connection)


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query, params or ())

        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None

        connection.commit()
        return result

    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Database error: {str(e)}")
        raise e

    finally:
        if cursor:
            cursor.close()
        if connection:
            release_db_connection(connection)


def choose_model(name, text):
    """
    Choose the model (ChatGPT or Bard) and get a response.
    """
    temperature = request.json.get('temperature')
    top_p = request.json.get('top_p')
    max_tokens = request.json.get('max_tokens')

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
    try:
        name = request.headers.get('X-name')
        text = request.json.get('text')
        chat_id = request.headers.get('X-chat-id')
        bot_id = request.headers.get('X-bot-id')
        message_order = request.json.get('message_order')

        if text is None:
            return jsonify({"message": "You cannot send an empty message"}), 400
        if chat_id is None:
            return jsonify({"message": "Unselected chat exception"}), 400
        if bot_id is None:
            return jsonify({"message": "Unselected bot exception"}), 400
        if user_id is None:
            return jsonify({"message": "Unauthorized"}), 401

        response, status_code = choose_model(name, text)
        if status_code != 200:
            return response, status_code

        u_gen = str(uuid.uuid4())
        b_gen = str(uuid.uuid4())

        # Insert user message
        user_timestamps = execute_query(
            """
            INSERT INTO message (message_id, message_order, sender_type, text, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING created_at, updated_at;
            """,
            (u_gen, message_order, 'user', text),
            fetch_one=True
        )
        created_at_user, updated_at_user = user_timestamps

        # Link user message to chat
        execute_query(
            """INSERT INTO chat_message (message_id, chat_id) VALUES (%s, %s)""",
            (u_gen, chat_id)
        )

        # Insert bot message
        bot_timestamps = execute_query(
            """
            INSERT INTO message (message_id, message_order, sender_type, text, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING created_at, updated_at;
            """,
            (b_gen, message_order + 1, 'bot', response),
            fetch_one=True
        )
        created_at_bot, updated_at_bot = bot_timestamps

        # Link bot message to chat
        execute_query(
            """INSERT INTO chat_message (message_id, chat_id) VALUES (%s, %s)""",
            (b_gen, chat_id)
        )

        return jsonify({
            "user_message": {
                "message_id": u_gen,
                "message_order": message_order,
                "sender_type": "user",
                "text": text,
                "created_at": created_at_user,
            },
            "bot_message": {
                "message_id": b_gen,
                "message_order": message_order + 1,
                "sender_type": "bot",
                "text": response,
                "created_at": created_at_bot,
            }
        }), status_code

    except Exception as e:
        logger.error(f"Error in ask_model: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/create', methods=['POST'])
@token_required
def create_chat(user_id):
    try:
        generated = str(uuid.uuid4())
        name = request.json.get('name')
        bot_id = request.json.get('bot_id')

        if not name or not bot_id:
            return jsonify({"message": "Name and bot_id are required"}), 400

        # Insert new chat
        created_at = execute_query(
            """
            INSERT INTO chat (chat_id, chat_name, user_id, bot_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING created_at;
            """,
            (generated, name, user_id, bot_id),
            fetch_one=True
        )

        # Fetch bot details
        bot = execute_query(
            """
            SELECT c.chat_name, b.bot_avatar, b.name
            FROM chat c
            JOIN bot b ON c.bot_id = b.bot_id
            WHERE c.bot_id = %s;
            """,
            (bot_id,),
            fetch_one=True
        )

        return jsonify({
            "chat_id": generated,
            "chat_name": bot[0],
            "bot_avatar": bot[1],
            "bot_name": bot[2],
            "created_at": created_at[0]
        }), 200

    except Exception as e:
        logger.error(f"Error in create_chat: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/user', methods=['GET'])
@token_required
def fetch_chats(user_id):
    try:
        user_chats = execute_query(
            """
            SELECT c.chat_id, c.chat_name, c.created_at, b.bot_avatar, b.name, b.bot_id
            FROM chat c
            JOIN bot b ON c.bot_id = b.bot_id
            WHERE c.user_id = %s;
            """,
            (user_id,),
            fetch_all=True
        )

        user_chats_objects = [
            {
                "chat_id": chat[0],
                "bot_id": chat[5],
                "user_id": user_id,
                "chat_name": chat[1],
                "bot_avatar": chat[3],
                "bot_name": chat[4],
                "created_at": chat[2],
            }
            for chat in user_chats
        ]

        return jsonify(user_chats_objects), 200

    except Exception as e:
        logger.error(f"Error in fetch_chats: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/<chatId>', methods=['GET'])
@token_required
def select_chat(user_id, chatId):
    try:
        chat = execute_query(
            """
            SELECT c.chat_name, b.bot_avatar, b.name, b.bot_id, u.user_avatar
            FROM chat c
            JOIN bot b ON b.bot_id = c.bot_id
            JOIN "user" u ON u.user_id = c.user_id
            WHERE c.user_id = %s AND c.chat_id = %s;
            """,
            (user_id, chatId),
            fetch_one=True
        )

        if not chat:
            return jsonify({"message": "Chat not found"}), 404

        return jsonify({
            "chat_id": chatId,
            "user_id": user_id,
            "bot_id": chat[3],
            "chat_name": chat[0],
            "bot_avatar": chat[1],
            "user_avatar": "pohuy 2",  # Replace with actual user avatar logic
            "bot_name": chat[2]
        }), 200

    except Exception as e:
        logger.error(f"Error in select_chat: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/<chatId>/delete', methods=['DELETE'])
@token_required
def delete_chat(user_id, chatId):
    try:
        # Delete chat messages
        messages_id = execute_query(
            """DELETE FROM chat_message WHERE chat_id = %s RETURNING message_id;""",
            (chatId,),
            fetch_all=True
        )

        for message_id in messages_id:
            execute_query(
                """DELETE FROM message WHERE message_id = %s;""",
                (message_id[0],)
            )

        # Delete chat
        execute_query(
            """DELETE FROM chat WHERE chat_id = %s;""",
            (chatId,)
        )

        return jsonify({"message": "Chat was deleted"}), 200

    except Exception as e:
        logger.error(f"Error in delete_chat: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500