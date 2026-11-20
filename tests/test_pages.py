import re
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent.parent / "acksec" / "templates"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_start_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "E-Banking" in response.get_data(as_text=True)


def test_unknown_page_gets_our_404(client):
    response = client.get("/gibt-es-nicht")
    assert response.status_code == 404
    assert "Seite nicht gefunden" in response.get_data(as_text=True)


def test_wrong_method_gets_405(client):
    response = client.post("/health")
    assert response.status_code == 405
    assert "Nicht erlaubt" in response.get_data(as_text=True)


def test_crash_shows_no_internals(app):
    @app.get("/crash")
    def crash():
        raise ValueError("db password is hunter2")

    response = app.test_client().get("/crash")
    body = response.get_data(as_text=True)

    assert response.status_code == 500
    assert "Interner Fehler" in body
    for leak in ("Traceback", "ValueError", "hunter2"):
        assert leak not in body


def test_crash_reference_is_the_request_id(app, caplog):
    @app.get("/crash")
    def crash():
        raise ValueError("boom")

    body = app.test_client().get("/crash").get_data(as_text=True)
    reference = re.search(r"<strong>([2-9A-Z]{8})</strong>", body).group(1)

    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert error_records
    assert error_records[-1].request_id == reference


def test_templates_have_no_inline_styles_or_scripts():
    for template in TEMPLATE_DIR.rglob("*.html"):
        content = template.read_text(encoding="utf-8")
        assert "style=" not in content, template.name
        assert "<script" not in content, template.name
        assert "<style" not in content, template.name
