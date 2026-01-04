import json
from pathlib import Path

MEMORY_FILE = Path("memory/format_memory.json")


def load_memory():
    if not MEMORY_FILE.exists():
        return {}
    return json.loads(MEMORY_FILE.read_text())


def save_memory(data):
    MEMORY_FILE.parent.mkdir(exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(data, indent=2))


def update_format(format_name: str, completion_rate: float, views: int):
    memory = load_memory()

    entry = memory.get(format_name, {
        "runs": 0,
        "avg_completion": 0,
        "avg_views": 0
    })

    entry["runs"] += 1
    entry["avg_completion"] = (
        (entry["avg_completion"] * (entry["runs"] - 1)) + completion_rate
    ) / entry["runs"]

    entry["avg_views"] = (
        (entry["avg_views"] * (entry["runs"] - 1)) + views
    ) / entry["runs"]

    memory[format_name] = entry
    save_memory(memory)
