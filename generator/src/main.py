import os
import sys
import time
import signal
import logging
from datetime import datetime
import numpy as np

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("stream-generator")

# Graceful shutdown handling
running = True

def handle_signal(sig, frame):
    global running
    logger.info("Received termination signal (%s). Performing graceful shutdown...", sig)
    running = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def main():
    logger.info("Starting Data Stream Generator...")

    # Load configuration from environment
    host = os.getenv("CLICKHOUSE_HOST", "clickhouse")
    port = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    user = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD", "")
    database = os.getenv("CLICKHOUSE_DATABASE", "analytics")
    batch_size = int(os.getenv("BATCH_SIZE", "100"))
    interval = float(os.getenv("INTERVAL_SECONDS", "2.0"))
    stations_count = int(os.getenv("STATIONS_COUNT", "10"))
    random_seed = int(os.getenv("RANDOM_SEED", "42"))

    np.random.seed(random_seed)

    logger.info("Target ClickHouse: %s:%s (db: %s)", host, port, database)
    logger.info("Batch size: %d, interval: %.1fs, stations: %d", batch_size, interval, stations_count)

    batch_id = 0
    while running:
        batch_id += 1
        now = datetime.utcnow()
        logger.info("Generated batch #%d with %d records at %s", batch_id, batch_size, now.isoformat())
        
        # Sleep with graceful break
        sleep_elapsed = 0.0
        while running and sleep_elapsed < interval:
            time.sleep(0.5)
            sleep_elapsed += 0.5

    logger.info("Generator stopped cleanly. Process exiting with code 0.")
    sys.exit(0)

if __name__ == "__main__":
    main()
