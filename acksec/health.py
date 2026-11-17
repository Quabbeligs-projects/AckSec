from flask import Blueprint

bp = Blueprint("health", __name__)


# docker and nginx use this to check if the app is up, so it must stay
# cheap and must not reveal anything about the system
@bp.get("/health")
def health():
    return {"status": "ok"}
