from flask import Blueprint, jsonify, request
from configuration import conn, cursor, token_required, ask_chatgpt, ask_wit, ask_bard
import uuid

chat_blueprint = Blueprint('chats', __name__)


def choose_model(name, text):

    temperature = request.json.get('temperature')
    top_p = request.json.get('top_p')
    max_tokens = request.json.get('max_tokens')

    if name == 'ChatGPT':

        if text is None:
            return "Prompt is missing", 400

        response, status_code = ask_chatgpt(text, temperature, top_p, max_tokens)
        return response, status_code

    elif name == 'Wit':

        if text is None:
            return "Prompt is missing", 400

        response, status_code = ask_wit(text)
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
        u_gen = str(uuid.uuid4())
        b_gen = str(uuid.uuid4())
        name = request.headers.get('X-name')
        text = request.json.get('text')
        chat_id = request.headers.get('X-chat-id')
        bot_id = request.headers.get('X-bot-id')
        message_order = request.json.get('message_order')

        if text is None:
            return jsonify({
                "message": "You can not send an empty message"
            }), 400

        if chat_id is None:
            return jsonify({
                "message": "Unselected chat exception"
            }), 400

        if bot_id is None:
            return jsonify({
                "message": "Unselected bot exception"
            })

        if user_id is None:
            print(user_id)
            return jsonify({
                "message": "Unauthorized"
            }), 401

        response, status_code = choose_model(name, text)

        if status_code != 200:
            return response, status_code

        cursor.execute(
            """
                INSERT INTO message
                VALUES (%s, %s, %s, %s, now(), now())
                RETURNING created_at, updated_at;
            """,
            (u_gen, message_order, 'user', text))
        user_timestamps = cursor.fetchone()
        created_at_user, updated_at_user = user_timestamps
        cursor.execute("""INSERT INTO chat_message VALUES (%s, %s)""", (u_gen, chat_id))
        conn.commit()
        cursor.execute(
            """
            INSERT INTO message
            VALUES (%s, %s, %s, %s, now(), now())
            RETURNING created_at, updated_at;
            """,
            (b_gen, message_order + 1, 'bot', response)
        )
        bot_timestamps = cursor.fetchone()
        created_at_bot, updated_at_bot = bot_timestamps
        cursor.execute("""INSERT INTO chat_message VALUES (%s, %s)""", (b_gen, chat_id))
        conn.commit()

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
        conn.rollback()
        print(str(e))
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
        cursor.execute("""INSERT INTO chat VALUES (%s, %s, %s, %s, now(), now()) RETURNING created_at""",
                       (generated, name, user_id, bot_id))
        created_at = cursor.fetchone()
        conn.commit()
        cursor.execute(
            """SELECT c.chat_name, b.bot_avatar, b.name FROM chat c JOIN bot b ON c.bot_id = b.bot_id WHERE c.bot_id = %s""",
            (bot_id,)
        )
        bot = cursor.fetchone()
        return jsonify({
            "chat_id": generated,
            "chat_name": bot[0],
            "bot_avatar": bot[1],
            "bot_name": bot[2],
            "created_at": created_at[0]
        }), 200

    except Exception as e:
        conn.rollback()
        print(str(e))

        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/user', methods=['GET'])
@token_required
def fetch_chats(user_id):
    try:
        cursor.execute("""SELECT c.chat_id, c.chat_name, c.created_at, b.bot_avatar, b.name, b.bot_id FROM """
                       """chat c JOIN bot b on c.bot_id = b.bot_id JOIN "user" u on u.user_id = c.user_id WHERE u.user_id = %s""", (user_id,))
        user_chats = cursor.fetchall()
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
        conn.rollback()
        print(str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/<chatId>', methods=['GET'])
@token_required
def select_chat(user_id, chatId):
    try:

        if chatId is None:
            return jsonify({
                "message": "Chat was not found"
            }), 400
        if user_id is None:
            return jsonify({
                "message": "User was not found"
            }), 400

        cursor.execute("""
            SELECT c.chat_name, b.bot_avatar, b.name, b.bot_id, u.user_avatar 
            FROM chat c 
            JOIN bot b ON b.bot_id = c.bot_id 
            JOIN "user" u ON u.user_id = c.user_id
            WHERE c.user_id = %s AND c.chat_id = %s
        """, (user_id, chatId))

        ch = cursor.fetchone()
        data = {
            "chat_id": chatId,
            "user_id": user_id,
            "bot_id": ch[3],
            "chat_name": ch[0],
            "bot_avatar": ch[1],
            "user_avatar": "pohuy 2",
            "bot_name": ch[2]
            }
        return jsonify(data), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@chat_blueprint.route('/<chatId>/delete', methods=['DELETE'])
@token_required
def delete_chat(user_id, chatId):

    cursor.execute("""DELETE FROM chat_message WHERE chat_id = %s RETURNING message_id""", (chatId,))
    messages_id = cursor.fetchall()
    for message_id in messages_id:
        cursor.execute("""DELETE FROM message WHERE message_id = %s""", (message_id, ))
    cursor.execute("""DELETE FROM chat WHERE chat_id = %s""", (chatId,))

    return jsonify({
        "message": "Chat was deleted",
    }), 200

