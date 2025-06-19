from functools import wraps
from flask import request, jsonify
from ..utils.jwt_utils import decode_jwt_token


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"message": "Unauthorized"}), 401

        user_id = decode_jwt_token(auth_header)
        if not user_id or isinstance(user_id, str) and user_id.startswith("Invalid"):
            return jsonify({"message": "Unauthorized"}), 401

        return f(user_id, *args, **kwargs)
    return decorated


def options_endpoint(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            response = jsonify()
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-bot-id, x-chat-id, x-name')
            response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS, POST, PUT, DELETE')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response, 200
        return f(*args, **kwargs)
    return decorated