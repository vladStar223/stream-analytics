FROM apache/superset:4.1.2
USER root
RUN pip install --no-cache-dir clickhouse-connect==0.8.18
COPY start.sh /app/start.sh
USER superset
CMD ["bash", "/app/start.sh"]
