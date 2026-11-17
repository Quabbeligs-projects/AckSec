# entry point for gunicorn: gunicorn wsgi:app
from acksec import create_app

app = create_app()
