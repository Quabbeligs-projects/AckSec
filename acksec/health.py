from flask import Blueprint

bp = Blueprint("health", __name__) # welcome to bp brother

@bp.get("/health")
def health():
    return {"status": "ok"}
