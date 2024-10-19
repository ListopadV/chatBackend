from flask import Flask, jsonify
from flask_cors import CORS
from psycopg2 import OperationalError, IntegrityError
from chat import chat_blueprint
from users import users_blueprint
from messages import messages_blueprint
from bots import bots_blueprint
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.register_blueprint(users_blueprint, url_prefix='/users')
app.register_blueprint(chat_blueprint, url_prefix='/chats')
app.register_blueprint(messages_blueprint, url_prefix='/messages')
app.register_blueprint(bots_blueprint, url_prefix='/bots')


@app.errorhandler(OperationalError)
def handle_db_connection_error(error):
    return jsonify({"error": "Database connection failed", "details": str(error)}), 500


@app.errorhandler(IntegrityError)
def handle_db_integrity_error(error):
    return jsonify({"error": "Integrity error in database operation", "details": str(error)}), 400


@app.errorhandler(Exception)
def handle_generic_error(error):
    return jsonify({"error": "An unexpected error occurred", "details": str(error)}), 500


CORS(app, origins=['https://chat-frontend-git-main-listopadiiiiks-projects.vercel.app/'])

if __name__ == "__main__":
    app.run(debug=True)
