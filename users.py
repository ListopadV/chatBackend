from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from configuration import conn, decode_jwt_token, create_jwt_token, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, connection_pool
import uuid
import requests

users_blueprint = Blueprint('users', __name__)


def get_db_connection():
    return connection_pool.getconn()


def release_db_connection(connection):
    if conn:
        connection_pool.putconn(connection)


@users_blueprint.route('/registration', methods=['POST'])
def registration():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
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
        conn.commit()

        release_db_connection(conn)  # Release the connection back to the pool

        response = jsonify({"message": "User was successfully registered", "access_token": create_jwt_token(generated)})
        return response, 200

    except Exception as e:
        if conn:
            conn.rollback()
            release_db_connection(conn)  # Ensure connection is released in case of error
        print("Error:", str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@users_blueprint.route('/login', methods=['POST'])
def login():
    try:
        conn = get_db_connection()  # Get a connection from the pool
        cursor = conn.cursor()
        data = request.json
        email = data.get('email')
        password = data.get('password')

        cursor.execute("""SELECT "user".password, "user".user_id FROM "user" WHERE "user".email = %s""", (email,))
        user = cursor.fetchone()

        if user is None:
            release_db_connection(conn)  # Release the connection if user is not found
            return jsonify({"message": "Wrong password or email"}), 400

        stored_password = user[0]
        if not check_password_hash(stored_password, password):
            release_db_connection(conn)  # Release the connection after check
            return jsonify({"message": "Wrong password or email"}), 400

        token = create_jwt_token(user[1])
        release_db_connection(conn)  # Release the connection after use

        return jsonify({"message": "User logged in successfully", "access_token": token}), 200

    except Exception as e:
        if conn:
            conn.rollback()
            release_db_connection(conn)  # Release the connection in case of error
        print(str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

    finally:
        connection_pool.putconn(conn)


@users_blueprint.route('/fetch', methods=['GET'])
def fetch():
    try:
        conn = get_db_connection()  # Get a connection from the pool
        cursor = conn.cursor()
        token = request.headers.get('Authorization')
        if token is None:
            release_db_connection(conn)  # Release connection if no token
            return jsonify({"message": "Unauthorized"}), 401

        user_id = decode_jwt_token(token)
        cursor.execute("""SELECT "user".first_name, "user".last_name, "user".email FROM "user" WHERE user_id = %s""", (user_id,))
        user = cursor.fetchone()
        if user is None:
            release_db_connection(conn)  # Release connection if user not found
            return jsonify({"error": "User was not found"}), 404

        response = jsonify({
            "first_name": user[0],
            "last_name": user[1],
            "email": user[2]
        })

        release_db_connection(conn)  # Release connection after use

        return response, 200

    except Exception as e:
        if conn:
            conn.rollback()
            release_db_connection(conn)  # Ensure connection is released in case of error
        print(str(e))
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

    finally:
        connection_pool.putconn(conn)


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
