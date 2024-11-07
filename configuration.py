import sys
import psycopg2
import jwt
import logging
import json
import boto3
import os
import sys
import datetime
from flask import request, jsonify
from functools import wraps
import requests
from dotenv import load_dotenv
import google.generativeai as genai
# from transformers import GPT2LMHeadModel, GPT2Tokenizer, pipeline, set_seed

load_dotenv()
host = os.getenv('host')
dbname = os.getenv('dbname')
user = os.getenv('user')
password = os.getenv('password')
sslmode = "require"
secret_key = os.getenv('secret_key')
api_key = os.getenv('api_key')
endpoint = os.getenv('endpoint')
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI')
wit_api_key = os.getenv('wit_api_key')
wit_endpoint = os.getenv('wit_endpoint')
gemini_api_key = os.getenv('gemini_api_key')
gemini_api_url = os.getenv('gemini_api_url')

logger = logging.getLogger(__name__)

try:
    conn = psycopg2.connect(
        host="ep-red-bird-a2w4s2p7-pooler.eu-central-1.aws.neon.tech",
        user="project_owner", password="CnyOFBI1GN7v",
        database="project", port="5432",
        sslmode='require')
except psycopg2.Error as e:
    logger.error('Could not establish connection with Postgre database')
    logger.error(e)
    sys.exit(0)

# generator = pipeline('text-generation', model="gpt2")
cursor = conn.cursor()


# def ask_gptj(text, temperature, top_p, max_tokens):
#     payload = {
#         "context": text,
#         "token_max_length": max_tokens,
#         "temperature": temperature,
#         "top_p": top_p
#     }
#     response = requests.post('http://api.vicgalle.net:5000/generate', params=payload)
#     print(response)
#     return "text gptj", 200

# def ask_gpt2(text, temperature, top_p, max_tokens):
#     try:
#         set_seed(42)
#         response = generator(text, max_length=300, num_return_sequences=1)
#         print(response)
#         return "check hug face", 200
#     except Exception as e:
#         return str(e), 500

    # def ask_chatgpt(text, temperature, top_p, max_tokens):
#     headers = {
#         "Content-type": "application/json",
#         "api-key": api_key
#     }
#     payload = {
#         "messages": [{
#             "role": "system",
#             "content": [
#                 {
#                     "type": "text",
#                     "text": text
#                 }
#             ]
#         }],
#         "temperature": temperature or 0.7,
#         "top_p": top_p or 0.95,
#         "max_tokens": max_tokens or 800
#     }
#     try:
#         response = requests.post(endpoint, headers=headers, json=payload)
#         response.raise_for_status()
#         response_data = response.json()
#         content = response_data['choices'][0]['message']['content']
#         return content, 200
#     except requests.exceptions.HTTPError as http_err:
#         error_data = http_err.response.json()
#         error_message = error_data['error']['message']
#         status_code = error_data['error']['code']
#         return error_message, status_code
#     except Exception as e:
#         return str(e), 500


def ask_wit(text):
    final_endpoint = wit_endpoint

    headers = {
        'Authorization': 'Bearer '+wit_api_key
    }
    params = {
        'q': text
    }
    try:
        response = requests.get(final_endpoint, headers=headers, params=params)
        response.raise_for_status()

    except requests.RequestException as e:
        raise SystemExit(f"Failed to make the request. Error: {e}")
    return response.json()


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

