from flask import Flask

from config import DEBUG, HOST, PORT, SECRET_KEY, SESSION_LIFETIME
from routes.api import api_bp
from routes.auth import auth_bp
from routes.pages import pages_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.permanent_session_lifetime = SESSION_LIFETIME

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    return app


app = create_app()


if __name__ == '__main__':
    print("=" * 60)
    print("Cardiac Segmentation QC Studio (multi-user)")
    print("=" * 60)
    print(f"Starting server on http://localhost:{PORT}")
    print("=" * 60)
    app.run(debug=DEBUG, host=HOST, port=PORT)
