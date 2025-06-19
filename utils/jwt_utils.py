import jwt
import datetime
from ..config import Config


def create_jwt_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
    return token


def decode_jwt_token(token):
    if not token.startswith('Bearer '):
        return None
    token = token[7:]
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None