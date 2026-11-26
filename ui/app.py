import os

import clickhouse_connect
import docker
import requests
from flask import Flask, abort, redirect, render_template_string, request

app = Flask(__name__)
SERVICES = ("clickhouse", "generator", "ui", "superset", "jupyter")


def client():
    return clickhouse_connect.get_client(host="clickhouse", username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"], database=os.environ["CLICKHOUSE_DATABASE"])


@app.get("/")
def index():
    with client() as ch:
        events = ch.query("SELECT timestamp, player_id, action_type, damage_dealt, ping_ms FROM fact_combat_events ORDER BY timestamp DESC LIMIT 25").result_rows
    containers = project_containers()
    status = requests.get("http://generator:9100/rate", timeout=3).json()
    return render_template_string("""
    <!doctype html><meta charset=utf-8><title>Телеметрия MMORPG</title>
    <h1>Телеметрия MMORPG</h1>
    <nav><a href="http://localhost:8088">Superset</a> · <a href="http://localhost:8888">Jupyter</a></nav>
    <h2>Сервисы и логи</h2>{% for c in containers %}<p><a href="/logs/{{c.labels['com.docker.compose.service']}}">{{c.name}}</a> · {{c.status}}</p>{% endfor %}
    <h2>Генератор</h2><p>{{status.mode}} · {{status.current_timestamp}}</p>
    <form method=post action="/rate"><label>Событий в батче <input type=number min=1 max=10000 name=batch_size value="{{status.batch_size}}"></label><button>Применить</button></form>
    <h2>Последние события</h2><table><tr><th>Время UTC<th>Игрок<th>Действие<th>Урон<th>Пинг, мс</tr>
    {% for row in events %}<tr>{% for value in row %}<td>{{value}}</td>{% endfor %}</tr>{% endfor %}</table>
    """, events=events, containers=containers, status=status)


def project_containers():
    with docker.from_env() as engine:
        return engine.containers.list(all=True, filters={"label": "com.docker.compose.project=" + os.environ["COMPOSE_PROJECT"]})


@app.get("/logs/<service>")
def logs(service):
    if service in SERVICES:
        for container in project_containers():
            if container.labels.get("com.docker.compose.service") == service:
                return container.logs(tail=100), 200, {"Content-Type": "text/plain; charset=utf-8"}
    abort(404)


@app.post("/rate")
def rate():
    size = request.form.get("batch_size", type=int)
    if size is None or not 1 <= size <= 10000:
        abort(400)
    requests.post("http://generator:9100/rate", json={"batch_size": size}, timeout=3).raise_for_status()
    return redirect("/")
