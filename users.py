from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from configuration import decode_jwt_token, create_jwt_token, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, connection_pool
import uuid
import requests

users_blueprint = Blueprint('users', __name__)


def get_db_connection():
    return connection_pool.getconn()


def release_db_connection(connection):
    if connection:
        connection_pool.putconn(connection)


@users_blueprint.route('/registration', methods=['POST'])
def registration():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        data = request.json
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        password = data.get('password')
        generated = str(uuid.uuid4())

        hashed_password = generate_password_hash(password)
        cursor.execute(
            """
            INSERT INTO "user" (user_id, first_name, last_name, email, password, user_avatar, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, 'pohuy 2', NOW(), NOW())
            """,
            (generated, first_name, last_name, email, hashed_password)
        )
        connection.commit()

        response = jsonify({"message": "User was successfully registered", "access_token": create_jwt_token(generated)})
        return response, 200

    except Exception as e:
        if connection:
            connection.rollback()
        print("Error:", str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

    finally:
        release_db_connection(connection)


@users_blueprint.route('/login', methods=['POST'])
def login():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        data = request.json
        email = data.get('email')
        password = data.get('password')

        cursor.execute("""SELECT "user".password, "user".user_id FROM "user" WHERE "user".email = %s""", (email,))
        user = cursor.fetchone()

        if user is None:
            return jsonify({"message": "Wrong password or email"}), 400

        stored_password = user[0]
        if not check_password_hash(stored_password, password):
            return jsonify({"message": "Wrong password or email"}), 400

        token = create_jwt_token(user[1])
        return jsonify({"message": "User logged in successfully", "access_token": token}), 200

    except Exception as e:
        connection.rollback()
        print(str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

    finally:
        release_db_connection(connection)


@users_blueprint.route('/fetch', methods=['GET'])
def fetch():
    try:
        connection = get_db_connection()  # Get a connection from the pool
        cursor = connection.cursor()
        token = request.headers.get('Authorization')
        if token is None:
            return jsonify({"message": "Unauthorized"}), 401

        user_id = decode_jwt_token(token)
        cursor.execute("""SELECT "user".first_name, "user".last_name, "user".email FROM "user" WHERE user_id = %s""", (user_id,))
        user = cursor.fetchone()
        if user is None:
            return jsonify({"error": "User was not found"}), 404

        response = jsonify({
            "first_name": user[0],
            "last_name": user[1],
            "email": user[2]
        })

        return response, 200

    except Exception as e:
        if connection:
            connection.rollback()
        print(str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

    finally:
        release_db_connection(connection)


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

    print(user_response)

    return {'access_token': access_token}
