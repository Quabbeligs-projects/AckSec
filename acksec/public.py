from flask import Blueprint, render_template

# pages anyone can see without logging in
bp = Blueprint("public", __name__)

@bp.get("/")
def index():
    return render_template("public/index.html")
