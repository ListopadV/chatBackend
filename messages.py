from flask import Blueprint, jsonify, request
from configuration import token_required, connection_pool, options_endpoint

messages_blueprint = Blueprint('messages', __name__)


def get_db_connection():
    return connection_pool.getconn()


def release_db_connection(connection):
    if connection:
        connection_pool.putconn(connection)


@messages_blueprint.route('/fetch', methods=['GET', 'OPTIONS'])
@token_required
@options_endpoint
def get_messages(user_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        chat_id = request.headers.get('X-chat-id')
        bot_id = request.headers.get('X-bot-id')

        if not chat_id:
            return jsonify({"message": "Unselected chat exception"}), 400

        if not bot_id:
            return jsonify({"message": "Unselected bot exception"}), 400

        cursor.execute(
            """
            SELECT m.message_id, m.message_order, m.sender_type, m.text, m.created_at 
            FROM message m 
            JOIN chat_message cm ON cm.message_id = m.message_id 
            JOIN chat c ON c.chat_id = cm.chat_id
            JOIN "user" u ON u.user_id = c.user_id 
            JOIN bot b ON b.bot_id = c.bot_id 
            WHERE b.bot_id = %s AND c.chat_id = %s AND u.user_id = %s 
            ORDER BY m.message_order ASC
            """,
            (bot_id, chat_id, user_id)
        )

        messages = cursor.fetchall()

        # Fetch bot avatar
        cursor.execute("SELECT bot_avatar FROM bot WHERE bot_id = %s", (bot_id,))
        bot_avatar = cursor.fetchone()
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

        response = jsonify({"messages": message_objects})
        return response, 200

    except Exception as e:
        connection.rollback()
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500
    finally:
        release_db_connection(connection)
