FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OIN_DATA_DIR=/var/lib/oin

WORKDIR /app

# Review and update the hash-locked dependency files intentionally; do not resolve
# unpinned dependencies during an image build.
COPY requirements-build.lock requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements-build.lock \
    && pip install --no-cache-dir --require-hashes -r requirements.lock

COPY pyproject.toml README.md ./
COPY oin ./oin
RUN pip install --no-cache-dir --no-deps --no-build-isolation .

RUN mkdir -p /var/lib/oin && useradd --system --home /var/lib/oin --uid 10001 oin \
    && chown -R oin:oin /app /var/lib/oin
USER oin

EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)" || exit 1
CMD ["uvicorn", "oin.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
