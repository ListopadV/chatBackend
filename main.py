from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import db
from .routes.users import users_blueprint
from .routes.chats import chat_blueprint
from .routes.messages import messages_blueprint
from .routes.bots import bots_blueprint


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    CORS(app,
         supports_credentials=True,
         resources={r"/*": {
             "origins": ['https://chat-frontend-vlo.vercel.app'],
             "allow_headers": [
                 "Content-Type", "Authorization",
                 "X-bot-id", "X-chat-id", "X-name"
             ],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
         }})

    app.register_blueprint(users_blueprint, url_prefix='/users')
    app.register_blueprint(chat_blueprint, url_prefix='/chats')
    app.register_blueprint(messages_blueprint, url_prefix='/messages')
    app.register_blueprint(bots_blueprint, url_prefix='/bots')

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
