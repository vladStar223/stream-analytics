#!/bin/bash
set -eu
clickhouse-client --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" --database "$CLICKHOUSE_DB" --multiquery <<'SQL'
CREATE TABLE IF NOT EXISTS dim_players (
    player_id UInt32, nickname String, char_class LowCardinality(String),
    faction LowCardinality(String), guild_name LowCardinality(String), server_realm LowCardinality(String)
) ENGINE = MergeTree ORDER BY player_id SETTINGS non_replicated_deduplication_window = 100;

CREATE TABLE IF NOT EXISTS fact_combat_events (
    event_id UUID, timestamp DateTime64(3, 'UTC'), player_id UInt32, player_level UInt8,
    action_type LowCardinality(String), combat_role Nullable(String), score_points UInt32,
    damage_dealt UInt64, healing_done UInt64, death_count UInt8, gold_delta Int64,
    ping_ms UInt16, difficulty Nullable(String), is_anomaly Bool
) ENGINE = MergeTree PARTITION BY toYYYYMM(timestamp) ORDER BY (timestamp, player_id, event_id)
SETTINGS non_replicated_deduplication_window = 100;

CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_realm_activity
ENGINE = SummingMergeTree ORDER BY (hour, server_realm) AS
SELECT toStartOfHour(e.timestamp) AS hour, p.server_realm AS server_realm,
       count() AS events, countIf(e.is_anomaly) AS anomalies
FROM fact_combat_events AS e INNER JOIN dim_players AS p ON e.player_id = p.player_id
GROUP BY hour, server_realm;
SQL
