FROM python:3.12-slim
RUN pip install --no-cache-dir jupyterlab pandas matplotlib clickhouse-connect
WORKDIR /home/jovyan/work
CMD ["jupyter", "lab", "--allow-root", "--ip=0.0.0.0", "--no-browser"]
