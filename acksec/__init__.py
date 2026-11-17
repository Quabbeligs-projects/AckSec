from flask import Flask


def create_app():
    # app factory instead of a global app object, so tests can build
    # their own instance with a different config later (C031)
    app = Flask(__name__)

    from acksec.health import bp as health_bp
    app.register_blueprint(health_bp)

    return app
