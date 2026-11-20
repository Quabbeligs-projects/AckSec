from flask import g, render_template
from werkzeug.exceptions import HTTPException, InternalServerError

from acksec.logging_setup import new_request_id

# Our short texts for these status codes, werkzeugs default ones are fine but some of them are a bit too verbose for my liking, also this way we can make them german for the teach
MESSAGES = {
    400: ("Ungültige Anfrage", "Die Anfrage konnte nicht verarbeitet werden. Bitte versuchen Sie es nochmals."),
    403: ("Kein Zugriff", "Sie haben keine Berechtigung für diese Seite."),
    404: ("Seite nicht gefunden", "Diese Seite gibt es nicht."),
    405: ("Nicht erlaubt", "Diese Aktion ist hier nicht möglich."),
    413: ("Anfrage zu gross", "Die gesendeten Daten sind zu gross."),
    429: ("Zu viele Anfragen", "Sie haben zu viele Anfragen gesendet. Bitte warten Sie einen Moment."),
    500: ("Interner Fehler", "Bei uns ist etwas schiefgelaufen. Der Fehler wurde protokolliert."),
}
FALLBACK = ("Fehler", "Die Anfrage konnte nicht verarbeitet werden.")


def _render(status, reference=None):
    title, text = MESSAGES.get(status, FALLBACK)
    return render_template(
        "error.html", status=status, title=title, text=text, reference=reference
    ), status

def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if isinstance(error, InternalServerError):
            return handle_unexpected_error(error.original_exception or error)
        return _render(error.code)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        reference = g.get("request_id") or new_request_id()
        app.logger.exception("unhandled error", exc_info=error)
        return _render(500, reference)
