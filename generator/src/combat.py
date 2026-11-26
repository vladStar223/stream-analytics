"""Synthetic per-character activity summaries in UTC."""
import math
import random
from uuid import UUID

CLASSES = ("Warrior", "Mage", "Priest", "Rogue", "Paladin")
REALMS = ("Gordunni", "Warsong", "Silvermoon")
ACTIONS = ("raid_boss", "pvp_arena", "mythic_dungeon", "crafting")
PLAYER_COLUMNS = ("player_id", "nickname", "char_class", "faction", "guild_name", "server_realm")
EVENT_COLUMNS = ("event_id", "timestamp", "player_id", "player_level", "action_type", "combat_role",
                 "score_points", "damage_dealt", "healing_done", "death_count", "gold_delta",
                 "ping_ms", "difficulty", "is_anomaly")


def players():
    return [(i, f"Hero{i:03}", CLASSES[i % 5], ("Alliance", "Horde")[i % 2],
             ("Aurora", "Tempest", "Ember", "Nova")[i % 4], REALMS[i % 3]) for i in range(1, 121)]


def activity(ts):
    return 0.65 + 0.35 * math.cos((ts.hour - 20) * math.pi / 12)


def event(ts, rng: random.Random, catalog, anomaly_rate):
    player, _, cls, _, _, realm = rng.choice(catalog)
    level = 1 + player * 17 % 80
    action = rng.choice(ACTIONS if level >= 60 else ("pvp_arena", "crafting"))
    fighting = action != "crafting"
    role = {"Warrior": "Tank", "Paladin": "Tank", "Priest": "Healer"}.get(cls, "DPS") if fighting else None
    damage = level * rng.randint(80, 140) * (3 if role == "DPS" else 1) if fighting else 0
    healing = level * rng.randint(120, 250) if role == "Healer" else 0
    ping = rng.randint(25, 65)
    lag = realm == REALMS[ts.day % 3] and ts.minute == 45
    spike = fighting and rng.random() < anomaly_rate
    difficulty = {"raid_boss": rng.choice(("Normal", "Heroic", "Mythic")), "mythic_dungeon": "Mythic"}.get(action)
    return (UUID(int=rng.getrandbits(128), version=4), ts, player, level, action, role,
            rng.randint(10, 100), damage * (50 if spike else 1), healing,
            rng.randrange(4) if fighting else 0, rng.randint(-50, 200),
            ping + (500 if lag else 0), difficulty, lag or spike)
