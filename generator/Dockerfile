FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir clickhouse-connect numpy

COPY src/ ./src/

CMD ["python", "-u", "src/main.py"]
