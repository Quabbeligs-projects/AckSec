FROM python:3.12-slim-bookworm AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY acksec/ acksec/
COPY wsgi.py .
COPY alembic.ini .
COPY migrations/ migrations/

RUN useradd --system --no-create-home --uid 10001 acksec
USER acksec

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--no-control-socket", "wsgi:app"]

FROM app AS test
USER root
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
USER acksec
CMD ["pytest"]
