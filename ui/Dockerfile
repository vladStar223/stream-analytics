FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask docker clickhouse-connect requests
COPY app.py .
CMD ["flask", "--app", "app", "run", "--host=0.0.0.0", "--port=8000"]
