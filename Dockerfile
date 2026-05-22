FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bridge.py /app/bridge.py
COPY i18n/ /app/i18n/
COPY providers/ /app/providers/
COPY providers.yaml /app/providers.yaml

EXPOSE 8000

CMD ["python", "bridge.py"]
