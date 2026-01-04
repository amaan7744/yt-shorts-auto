import json
from pathlib import Path
from datetime import datetime

TIME_MEMORY_FILE = Path("memory/time_slot_memory.json")


def load_time_memory():
    if not TIME_MEMORY_FILE.exists():
        return {}
    return json.loads(TIME_MEMORY_FILE.read_text())


def save_time_memory(data):
    TIME_MEMORY_FILE.parent.mkdir(exist_ok=True)
    TIME_MEMORY_FILE.write_text(json.dumps(data, indent=2))


def register_upload_result(completion_rate: float):
    """
    Records performance for the current upload hour.
    """

    hour = str(datetime.utcnow().hour)
    memory = load_time_memory()

    entry = memory.get(hour, {
        "runs": 0,
        "avg_completion": 0
    })

    entry["runs"] += 1
    entry["avg_completion"] = (
        (entry["avg_completion"] * (entry["runs"] - 1)) + completion_rate
    ) / entry["runs"]

    memory[hour] = entry
    save_time_memory(memory)


def best_hours(min_runs: int = 3):
    """
    Returns best performing hours.
    """

    memory = load_time_memory()

    ranked = [
        (h, d) for h, d in memory.items()
        if d["runs"] >= min_runs
    ]

    ranked.sort(key=lambda x: x[1]["avg_completion"], reverse=True)

    return [h for h, _ in ranked[:3]]
