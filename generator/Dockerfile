FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir clickhouse-connect==0.8.18
COPY src/ ./
CMD ["python", "main.py"]
