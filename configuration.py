import jwt
from psycopg2 import pool
import logging
import os
import datetime
from flask import request, jsonify
from functools import wraps
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI

load_dotenv()
host = os.getenv('POSTGRES_HOST')
dbname = os.getenv('POSTGRES_DB')
user = os.getenv('POSTGRES_USER')
password = os.getenv('POSTGRES_PASSWORD')
secret_key = os.getenv('SECRET_KEY')
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI')
gemini_api_key = os.getenv('GEMINI_API_KEY')
gemini_api_url = os.getenv('GEMINI_API_URL')
api_key = os.getenv('OPENAI_API_KEY')


if api_key is None:
    print("Error: OPENAI_API_KEY environment variable not set")
else:
    print("API key retrieved successfully")

client = OpenAI(api_key=api_key)

logger = logging.getLogger(__name__)

connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    user=user,
    password=password,
    host=host,
    port=5432,
    dbname=dbname
)



def ask_gpt(text, temperature, top_p, max_tokens):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": text}
            ],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )
        response = completion.choices[0].message.content
        return response, 200
    except Exception as e:
        return str(e), 500


def ask_bard(text, temperature, top_p, max_tokens):
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            text,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=max_tokens
            )
        )
        return response.text, 200
    except requests.exceptions.HTTPError as http_err:
        error_data = http_err.response.json()
        error_message = error_data['error']['message']
        status_code = error_data['error']['code']
        return error_message, status_code
    except Exception as e:
        return str(e), 500


def create_jwt_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


def decode_jwt_token(token):
    if not token.startswith('Bearer '):
        return "Invalid token type. Use Bearer <token>"
    token = token[7:]
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return "Token was expired. Please log in again"
    except jwt.InvalidTokenError:
        return "Invalid token. Please log in again"


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_render = request.headers.get('Authorization')
        if not auth_render:
            return jsonify({
                "message": "Unauthorized"
            }), 401
        if not auth_render.startswith("Bearer "):
            return jsonify({
                "message": "Unauthorized"
            }), 401

        user_id = decode_jwt_token(auth_render)
        return f(user_id, *args, **kwargs)
    return decorated


def options_endpoint(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            response = jsonify()
            response.headers.add('Access-Control-Allow-Origin', 'https://chat-frontend-vlo.vercel.app')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, x-bot-id, x-chat-id, x-name')
            response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response, 200
        return f(*args, **kwargs)
    return decorated