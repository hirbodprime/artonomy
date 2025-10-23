# ---- base ----
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# ---- deps ----
FROM base AS deps
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- app ----
FROM base AS app
COPY --from=deps /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=deps /usr/local/bin /usr/local/bin
COPY . /app
# create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# collect static at runtime via entrypoint (prod)
ENV PORT=8000
EXPOSE 8000
CMD ["./entrypoint.sh"]
