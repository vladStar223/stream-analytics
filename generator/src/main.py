"""Resume from the latest stored timestamp, backfill history, then stream live batches."""
import logging
import os
import random
import signal
from datetime import UTC, datetime, timedelta
from threading import Event

import clickhouse_connect
from clickhouse_connect.driver.exceptions import OperationalError
from combat import EVENT_COLUMNS, PLAYER_COLUMNS, activity, event, players
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
    interval = float(os.getenv("INTERVAL_SECONDS", "2"))
    days = int(os.getenv("BACKFILL_DAYS", "7"))
    probability = float(os.getenv("ANOMALY_RATE", "0.02"))
    seed = int(os.getenv("RANDOM_SEED", "42"))
    if interval <= 0 or days < 0 or not 0 <= probability <= 1:
        raise ValueError("Invalid interval, history length or anomaly probability")
    catalog = players()
    with retry(lambda: clickhouse_connect.get_client(host=os.environ["CLICKHOUSE_HOST"],
               port=int(os.environ["CLICKHOUSE_PORT"]), username=os.environ["CLICKHOUSE_USER"],
               password=os.environ["CLICKHOUSE_PASSWORD"], database=os.environ["CLICKHOUSE_DATABASE"])) as db:
        known = set(retry(lambda: db.query("SELECT player_id FROM dim_players").result_columns[0]))
        missing = [p for p in catalog if p[0] not in known]
        if missing:
            retry(lambda: db.insert("dim_players", missing, column_names=PLAYER_COLUMNS))
        now = datetime.now(UTC)
        start = now - timedelta(days=days)
        last_ms = retry(lambda: db.command("SELECT maxOrNull(toUnixTimestamp64Milli(timestamp)) FROM fact_combat_events"))
        cursor = datetime.fromtimestamp(last_ms / 1000, UTC) if last_ms is not None else start
        while not stop.is_set():
            now = datetime.now(UTC)
            historical = (now - cursor).total_seconds() > max(120, interval * 2)
            size = status.batch_size
            if historical:
                times = []
                while len(times) < size and cursor < now - timedelta(seconds=60):
                    cursor = min(now, cursor + timedelta(seconds=30 / activity(cursor)))
                    times.append(cursor)
            else:
                if stop.wait(interval):
                    break
                end = datetime.now(UTC)
                if end <= cursor:
                    continue
                count = max(1, round(size * activity(end)))
                times = [cursor + (end - cursor) * (i / count) for i in range(1, count + 1)]
                cursor = end
            rng = random.Random(f"{seed}-{times[0].isoformat()}")
            batch = [event(ts, rng, catalog, probability) for ts in times]
            retry(lambda: db.insert("fact_combat_events", batch, column_names=EVENT_COLUMNS))
            progress = min(100, max(0, 100 * (cursor - start) / max(now - start, timedelta(seconds=1))))
            status.update(mode="backfill" if historical else "realtime", current_timestamp=cursor, progress_pct=progress)
            log.info("Inserted %d events through %s", len(batch), cursor)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    status = GeneratorStatus(int(os.getenv("BATCH_SIZE", "100")))
    status.set_batch_size(status.batch_size)
    control = ControlServer(status, "0.0.0.0", 9100, stop).start()
    try:
        run(status)
    except InterruptedError:
        pass
    finally:
        control.stop()
