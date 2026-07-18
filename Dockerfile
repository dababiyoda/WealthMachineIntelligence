FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/opt/uat-venv

WORKDIR /build

RUN python -m pip install --no-cache-dir uv==0.11.28

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/uat-venv/bin:$PATH \
    PORT=5000

WORKDIR /app

RUN groupadd --system uat \
    && useradd --system --gid uat --home-dir /app uat \
    && mkdir -p /data \
    && chown -R uat:uat /app /data

COPY --from=builder /opt/uat-venv /opt/uat-venv

COPY --chown=uat:uat . .

USER uat
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health/ready', timeout=3)" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "5000", "--proxy-headers"]
