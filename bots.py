from configuration import token_required
from flask import Blueprint, request, jsonify
import uuid
import logging
from configuration import connection_pool

bots_blueprint = Blueprint('bots', __name__)
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



@bots_blueprint.route('/create', methods=['POST'])
@token_required
def create_bot():
    try:
        generated = str(uuid.uuid4())
        name = request.json.get('name')
        model = request.json.get('model')
        avatar = request.json.get('avatar')
        description = request.json.get('description')

        create_bot_query = """
            INSERT INTO bot (bot_id, name, model, bot_avatar, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, now(), now())
        """
        execute_query(create_bot_query, (generated, name, model, avatar, description))

        response = jsonify({
            "bot_id": generated,
            "name": name,
            "model": model,
            "bot_avatar": avatar
        })
        return response, 200

    except Exception as e:
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@bots_blueprint.route('/bots', methods=['GET'])
@token_required
def get_bots(user_id):
    try:
        fetch_bots_query = """
            SELECT bot_id, name, model, bot_avatar, description, created_at, updated_at FROM bot
        """
        info = execute_query(fetch_bots_query, fetch_all=True)

        if not info:
            return jsonify({"message": "No bots were found"}), 200

        info_objects = [
            {
                "bot_id": bot[0],
                "name": bot[1],
                "model": bot[2],
                "bot_avatar": bot[3],
                "description": bot[4],
                "created_at": bot[5],
                "updated_at": bot[6],
            }
            for bot in info
        ]

        response = jsonify({"bots": info_objects})
        return response, 200

    except Exception as e:
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500
