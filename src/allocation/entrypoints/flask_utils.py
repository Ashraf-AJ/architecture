from collections import deque
from flask import Flask, g


def create_app():
    app = Flask(__name__)

    @app.before_request
    def set_message_queue():
        g.message_queue = deque()

    return app


def get_message_queue():
    return g.message_queue
