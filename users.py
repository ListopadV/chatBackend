from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from configuration import decode_jwt_token, create_jwt_token, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, connection_pool
import uuid
import requests
import logging


users_blueprint = Blueprint('users', __name__)

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


@users_blueprint.route('/registration', methods=['POST'])
def registration():
    try:
        data = request.json
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        password = data.get('password')
        generated = str(uuid.uuid4())

        hashed_password = generate_password_hash(password)
        execute_query(
            """
            INSERT INTO "user" (user_id, first_name, last_name, email, password, user_avatar, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, 'pohuy 2', NOW(), NOW())
            """,
            (generated, first_name, last_name, email, hashed_password)
        )

        response = jsonify({"message": "User was successfully registered", "access_token": create_jwt_token(generated)})
        return response, 200

    except Exception as e:
        logger.error(f"Error in registration: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@users_blueprint.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        user = execute_query(
            """SELECT "user".password, "user".user_id FROM "user" WHERE "user".email = %s""",
            (email,),
            fetch_one=True
        )

        if user is None:
            return jsonify({"message": "Wrong password or email"}), 400

        stored_password = user[0]
        if not check_password_hash(stored_password, password):
            return jsonify({"message": "Wrong password or email"}), 400

        token = create_jwt_token(user[1])
        return jsonify({"message": "User logged in successfully", "access_token": token}), 200

    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@users_blueprint.route('/fetch', methods=['GET'])
def fetch():
    try:
        token = request.headers.get('Authorization')
        if token is None:
            return jsonify({"message": "Unauthorized"}), 401

        user_id = decode_jwt_token(token)
        user = execute_query(
            """SELECT "user".first_name, "user".last_name, "user".email FROM "user" WHERE user_id = %s""",
            (user_id,),
            fetch_one=True
        )

        if user is None:
            return jsonify({"error": "User was not found"}), 404

        response = jsonify({
            "first_name": user[0],
            "last_name": user[1],
            "email": user[2]
        })

        return response, 200

    except Exception as e:
        logger.error(f"Error in fetch: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@users_blueprint.route('/callback', methods=['POST'])
def callback():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        return response, 204

    code = request.args.get('code')
    token_response = requests.post('https://github.com/login/oauth/access_token', data={
        'client_id': GITHUB_CLIENT_ID,
        'client_secret': GITHUB_CLIENT_SECRET,
        'code': code,
    }, headers={'Accept': 'application/json'})

    access_token = token_response.json().get('access_token')

    user_response = requests.get('https://api.github.com/user', headers={
        'Authorization': f'token {access_token}',
        'Accept': 'application/json'
    })

    logger.info(f"GitHub user response: {user_response.json()}")

    return {'access_token': access_token}