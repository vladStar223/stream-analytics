#!/bin/bash
set -eu
superset db upgrade
superset fab create-admin --username admin --firstname Local --lastname Admin --email admin@localhost.local --password "$SUPERSET_ADMIN_PASSWORD"
superset init
python - <<'PY'
import os
from sqlalchemy.engine import URL
from superset.app import create_app
from superset.extensions import db

with create_app().app_context():
    from superset.models.core import Database
    connection = db.session.query(Database).filter_by(database_name="ClickHouse").one_or_none()
    if connection is None:
        connection = Database(database_name="ClickHouse")
        db.session.add(connection)
    uri = URL.create("clickhousedb", username=os.environ["CLICKHOUSE_USER"],
                     password=os.environ["CLICKHOUSE_PASSWORD"], host="clickhouse",
                     port=8123, database=os.environ["CLICKHOUSE_DATABASE"])
    connection.set_sqlalchemy_uri(uri.render_as_string(hide_password=False))
    db.session.commit()
PY
exec gunicorn -b 0.0.0.0:8088 --timeout 120 'superset.app:create_app()'
