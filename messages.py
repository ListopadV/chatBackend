from flask import Blueprint, jsonify, request
from configuration import conn, token_required, connection_pool
import logging

messages_blueprint = Blueprint('messages', __name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


@messages_blueprint.route('/fetch', methods=['GET'])
@token_required
def get_messages(user_id):
    try:
        chat_id = request.headers.get('X-chat-id')
        bot_id = request.headers.get('X-bot-id')

        if not chat_id:
            return jsonify({"message": "Unselected chat exception"}), 400

        if not bot_id:
            return jsonify({"message": "Unselected bot exception"}), 400

        # Fetch messages
        messages_query = """
            SELECT m.message_id, m.message_order, m.sender_type, m.text, m.created_at 
            FROM message m 
            JOIN chat_message cm ON cm.message_id = m.message_id 
            JOIN chat c ON c.chat_id = cm.chat_id
            JOIN "user" u ON u.user_id = c.user_id 
            JOIN bot b ON b.bot_id = c.bot_id 
            WHERE b.bot_id = %s AND c.chat_id = %s AND u.user_id = %s 
            ORDER BY m.message_order ASC
        """
        messages = execute_query(messages_query, (bot_id, chat_id, user_id), fetch_all=True)

        # Fetch bot avatar
        avatar_query = "SELECT bot_avatar FROM bot WHERE bot_id = %s"
        bot_avatar = execute_query(avatar_query, (bot_id,), fetch_one=True)
        bot_avatar = bot_avatar[0] if bot_avatar else "no avatar"

        # User avatar placeholder
        user_avatar = "no ava"

        # Prepare message objects
        message_objects = [
            {
                "message_id": message[0],
                "message_order": message[1],
                "sender_type": message[2],
                "text": message[3],
                "created_at": message[4],
                "avatar": bot_avatar if message[2] == 'bot' else user_avatar
            }
            for message in messages if message[2] in ['bot', 'user']
        ]

        return jsonify({"messages": message_objects}), 200

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500
