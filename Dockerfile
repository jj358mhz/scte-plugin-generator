# syntax=docker/dockerfile:1.7

# =============================================================================
# scte-plugin-generator — Flask app for generating SCTE-35 plugin scaffolds
# =============================================================================
# Multi-stage build:
#   builder — installs Python deps into a venv
#   runtime — copies the venv + app source into a slim base
#
# Deployment: Portainer polls this repo, rebuilds the image, restarts the
# container. Fronted by Caddy at plugin.telcomjj.com.
# -----------------------------------------------------------------------------

# --- builder stage -----------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

# Build deps only — no compiler needed for Flask/Jinja2 pure-Python wheels,
# but keeping gcc available covers future deps that might need it.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Isolated venv so the runtime stage just copies /opt/venv without pip
# metadata bloat.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn==22.0.0

# --- runtime stage -----------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Non-root user — matches the pattern from your other Utility Pi stacks and
# avoids the container running as UID 0.
RUN groupadd --system --gid 1000 app \
    && useradd  --system --uid 1000 --gid app --home /app --shell /usr/sbin/nologin app

# Runtime deps only. tini reaps zombie children if a gunicorn worker forks
# and dies — small insurance for long-running containers.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --chown=app:app app.py .
COPY --chown=app:app templates/ ./templates/
COPY --chown=app:app static/ ./static/

USER app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/healthz',timeout=2).getcode()==200 else 1)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
