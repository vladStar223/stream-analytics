"""Resume from the latest stored timestamp, backfill history, then stream live batches."""
import logging
import os
import random
import signal
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event

import clickhouse_connect
from clickhouse_connect.driver.exceptions import OperationalError
from combat import EVENT_COLUMNS, PLAYER_COLUMNS, event, players
from control import ControlServer, GeneratorStatus

stop = Event()
log = logging.getLogger("generator")


def retry(operation):
    delay = 1
    while not stop.is_set():
        try:
            return operation()
        except (OperationalError, OSError) as exc:
            log.warning("ClickHouse unavailable (%s), retry in %ss", exc, delay)
            stop.wait(delay)
            delay = min(30, 2 * delay)
    raise InterruptedError


def run(status):
    start = datetime.fromisoformat(os.getenv("GENERATOR_BACKFILL_START", "2025-01-01T00:00:00"))
    start = start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
    history_step = timedelta(seconds=float(os.getenv("GENERATOR_BACKFILL_STEP_SECONDS", "60")))
    live_step = timedelta(seconds=float(os.getenv("GENERATOR_REALTIME_STEP_SECONDS", "1")))
    probability = float(os.getenv("GENERATOR_ANOMALY_PROBABILITY", "0.02"))
    seed = int(os.getenv("GENERATOR_SEED", "42"))
    if min(history_step, live_step) < timedelta(milliseconds=1) or not 0 <= probability <= 1:
        raise ValueError("Steps must be at least 1 ms and anomaly probability between 0 and 1")
    catalog = players()
    database = os.environ["CLICKHOUSE_DATABASE"]
    params = dict(host=os.environ["CLICKHOUSE_HOST"], port=int(os.environ["CLICKHOUSE_PORT"]),
                  username=os.environ["CLICKHOUSE_USER"], password=os.environ["CLICKHOUSE_PASSWORD"])
    with retry(lambda: clickhouse_connect.get_client(**params, database="default")) as admin:
        retry(lambda: admin.command("CREATE DATABASE IF NOT EXISTS {db:Identifier}", parameters={"db": database}))
    with retry(lambda: clickhouse_connect.get_client(**params, database=database)) as db:
        for statement in Path(__file__).with_name("schema.sql").read_text().split(";"):
            if statement.strip():
                retry(lambda: db.command(statement))
        known = {row[0] for row in retry(lambda: db.query("SELECT player_id FROM dim_players").result_rows)}
        missing = [p for p in catalog if p[0] not in known]
        if missing:
            retry(lambda: db.insert("dim_players", missing, column_names=PLAYER_COLUMNS))
        cutoff = datetime.now(UTC)
        last_ms = retry(lambda: db.query(
            "SELECT maxOrNull(toUnixTimestamp64Milli(timestamp)) FROM fact_combat_events"
        ).result_rows[0][0])
        next_ts = start
        if last_ms is not None:
            last = datetime.fromtimestamp(last_ms / 1000, UTC)
            if last >= start:
                next_ts = last + history_step
        while not stop.is_set():
            historical = next_ts <= cutoff
            if historical:
                count = min(status.batch_size, (cutoff - next_ts) // history_step + 1)
                step = history_step
            else:
                delay = (next_ts - datetime.now(UTC)).total_seconds()
                if delay > 0 and stop.wait(delay):
                    break
                count, step = 1, live_step
            rng = random.Random(f"{seed}-{next_ts.isoformat()}")
            batch = [event(next_ts + i * step, rng, catalog, probability) for i in range(count)]
            retry(lambda: db.insert("fact_combat_events", batch, column_names=EVENT_COLUMNS))
            latest = batch[-1][1]
            next_ts = latest + step
            progress = min(100, 100 * (next_ts - start) / max(cutoff - start, timedelta(seconds=1)))
            status.update(mode="backfill" if historical else "realtime", current_timestamp=latest, progress_pct=progress)
            log.info("Inserted %d events through %s", count, latest)
            if not historical:
                stop.wait(live_step.total_seconds())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    status = GeneratorStatus(int(os.getenv("GENERATOR_BATCH_SIZE", "1000")))
    status.set_batch_size(status.batch_size)
    control = ControlServer(status, "0.0.0.0", 9100, stop).start()
    try:
        run(status)
    except InterruptedError:
        pass
    finally:
        control.stop()
