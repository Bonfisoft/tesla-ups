FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install dependencies and curl for healthcheck
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY bridge.py /app/bridge.py
COPY i18n/ /app/i18n/
COPY providers/ /app/providers/
COPY providers.yaml /app/providers.yaml

EXPOSE 8000

# Healthcheck: verify API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

CMD ["python", "bridge.py"]
