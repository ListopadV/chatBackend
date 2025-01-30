from configuration import decode_jwt_token, token_required, options_endpoint
from flask import Blueprint, request, jsonify
import uuid
from configuration import connection_pool

bots_blueprint = Blueprint('bots', __name__)


def get_db_connection():
    return connection_pool.getconn()


def release_db_connection(connection):
    if connection:
        connection_pool.putconn(connection)


@bots_blueprint.route('/create', methods=['POST'])
@token_required
# @options_endpoint
def create_bot():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        generated = str(uuid.uuid4())
        name = request.json.get('name')
        model = request.json.get('model')
        avatar = request.json.get('avatar')
        description = request.json.get('description')
        cursor.execute("INSERT INTO bot VALUES (%s, %s, %s, %s, %s, now(), now())",
         (generated, name, model, avatar, description))
        connection.commit()

        response = jsonify({
            "bot_id": generated,
            "name": name,
            "model": model,
            "bot_avatar": avatar
        })
        return response, 200

    except Exception as e:
        connection.rollback()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

    finally:
        release_db_connection(connection)


@bots_blueprint.route('/bots', methods=['GET'])
@token_required
# @options_endpoint
def get_bots(user_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT bot_id, name, model, bot_avatar, description, created_at, updated_at FROM bot
        """)
        info = cursor.fetchall()

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
        return response, 200

    except Exception as e:
        connection.rollback()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

    finally:
        release_db_connection(connection)
