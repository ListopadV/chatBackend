from configuration import decode_jwt_token, token_required
from flask import Blueprint, request, jsonify
import uuid
from configuration import cursor, conn

bots_blueprint = Blueprint('bots', __name__)


@bots_blueprint.route('/create', methods=['POST'])
@token_required
def create_bot():

    try:
        generated = str(uuid.uuid4())
        name = request.json.get('name')
        model = request.json.get('model')
        avatar = request.json.get('avatar')
        description = request.json.get('description')
        cursor.execute("INSERT INTO bot VALUES (%s, %s, %s, %s, %s, now(), now())", (generated, name, model, avatar, description))
        conn.commit()

        response = jsonify({
            "bot_id": generated,
            "name": name,
            "model": model,
            "bot_avatar": avatar
        })
        response.headers['Access-Control-Allow-Origin'] = 'https://chat-frontend-vlo.vercel.app'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response, 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@bots_blueprint.route('/motherfuckers', methods=['GET'])
@token_required
def get_bots(user_id):
    try:
        cursor.execute("""
            SELECT bot.bot_id, bot.name, bot.model, bot.bot_avatar, bot.description, bot.created_at, bot.updated_at FROM bot
        """)
        info = cursor.fetchall()
        print(info)

        if len(info) == 0:
            return jsonify({"message": "No bots were found"}), 200

        info_objects = []
        for bot in info:
            info_objects.append({
                "bot_id": bot[0],
                "name": bot[1],
                "model": bot[2],
                "bot_avatar": bot[3],
                "description": bot[4],
                "created_at": bot[5],
                "updated_at": bot[6],
            })
        response = jsonify({"bots": info_objects})
        response.headers['Access-Control-Allow-Origin'] = 'https://chat-frontend-vlo.vercel.app'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response, 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500
