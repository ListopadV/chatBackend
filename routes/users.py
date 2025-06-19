from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from ..models.user import User
from ..schemas.user import UserSchema
from ..extensions import db
from ..utils.jwt_utils import create_jwt_token, decode_jwt_token
from ..utils.decorators import token_required
from ..config import Config
import uuid
import requests


users_blueprint = Blueprint('users', __name__)
user_schema = UserSchema()


@users_blueprint.route('/registration', methods=['POST'])
def registration():
    data = request.json
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')
    generated = str(uuid.uuid4())

    if not all([first_name, last_name, email, password]):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 409

    try:
        hashed_password = generate_password_hash(password)
        user = User(
            user_id=generated,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            user_avatar='pohuy 2'
        )
        db.session.add(user)
        db.session.commit()
        response = jsonify({
            "message": "User was successfully registered",
            "access_token": create_jwt_token(generated)
        })
        return response, 200
    except Exception as e:
        db.session.rollback()
        print("Error:", str(e))
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


@users_blueprint.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({"message": "Missing email or password"}), 400

    try:
        user = User.query.filter_by(email=email).first()
        if user is None:
            return jsonify({"message": "User with this email does not exist"}), 404

        if not check_password_hash(user.password, password):
            return jsonify({"message": "Wrong password or email"}), 400

        token = create_jwt_token(user.user_id)
        return jsonify({
            "message": "User logged in successfully",
            "access_token": token
        }), 200

    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


@users_blueprint.route('/fetch', methods=['GET'])
@token_required
def fetch(user_id):
    try:
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            return jsonify({"error": "User was not found"}), 404

        data = user_schema.dump(user)
        response = jsonify({
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "email": data["email"]
        })
        return response, 200
    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


@users_blueprint.route('/callback', methods=['POST'])
def callback():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        return response, 204

    code = request.args.get('code')
    token_response = requests.post('https://github.com/login/oauth/access_token', data={
        'client_id': Config.GITHUB_CLIENT_ID,
        'client_secret': Config.GITHUB_CLIENT_SECRET,
        'code': code,
    }, headers={'Accept': 'application/json'})

    access_token = token_response.json().get('access_token')

    user_response = requests.get('https://api.github.com/user', headers={
        'Authorization': f'token {access_token}',
        'Accept': 'application/json'
    })

    print(user_response)
    return {'access_token': access_token}
