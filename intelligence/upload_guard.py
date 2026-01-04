import json
from pathlib import Path
from datetime import datetime, timedelta

LOG = Path("memory/performance_log.json")

MAX_BAD_RUNS = 3
PAUSE_HOURS = 24


def should_pause_uploads():
    if not LOG.exists():
        return False

    data = json.loads(LOG.read_text())
    recent = list(data.values())[-MAX_BAD_RUNS:]

    if len(recent) < MAX_BAD_RUNS:
        return False

    bad = all(v["verdict"] in ("kill", "average") for v in recent)

    return bad
