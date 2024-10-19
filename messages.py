from flask import Blueprint, jsonify, request
from configuration import conn, cursor, token_required

messages_blueprint = Blueprint('messages', __name__)


@messages_blueprint.route('/fetch', methods=['GET'])
@token_required
def get_messages(user_id):
    try:
        chat_id = request.headers.get('X-chat-id')
        bot_id = request.headers.get('X-bot-id')

        if chat_id is None:
            return jsonify({
                "message": "Unselected chat exception"
            })

        if bot_id is None:
            return jsonify({
                "message": "Unselected bot exception"
            })

        cursor.execute("""
            SELECT m.message_id, m.message_order, m.sender_type, m.text, m.created_at 
            FROM message m 
            JOIN chat_message cm ON cm.message_id = m.message_id 
            JOIN chat c ON c.chat_id = cm.chat_id
            JOIN "user" u ON u.user_id = c.user_id 
            JOIN bot b ON b.bot_id = c.bot_id 
            WHERE b.bot_id = %s AND c.chat_id = %s AND u.user_id = %s ORDER BY m.message_order asc
        """, (bot_id, chat_id, user_id))

        messages = cursor.fetchall()
        # cursor.execute("SELECT user_avatar FROM user WHERE user_id = %s", (user_id,))
        # user_avatar = cursor.fetchone()

        user_avatar = "no ava"
        cursor.execute("SELECT bot_avatar FROM bot WHERE bot_id = %s", (bot_id, ))
        bot_avatar = cursor.fetchone()

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

        return jsonify({
            "messages": message_objects
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500
