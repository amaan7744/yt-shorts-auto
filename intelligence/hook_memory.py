import json
from pathlib import Path

HOOK_MEMORY_FILE = Path("memory/hook_memory.json")


def load_hook_memory():
    if not HOOK_MEMORY_FILE.exists():
        return {}
    return json.loads(HOOK_MEMORY_FILE.read_text())


def save_hook_memory(data):
    HOOK_MEMORY_FILE.parent.mkdir(exist_ok=True)
    HOOK_MEMORY_FILE.write_text(json.dumps(data, indent=2))


def register_hook_result(hook_text: str, completion_rate: float):
    """
    Updates hook performance memory.
    """

    memory = load_hook_memory()

    entry = memory.get(hook_text, {
        "runs": 0,
        "avg_completion": 0
    })

    entry["runs"] += 1
    entry["avg_completion"] = (
        (entry["avg_completion"] * (entry["runs"] - 1)) + completion_rate
    ) / entry["runs"]

    memory[hook_text] = entry
    save_hook_memory(memory)


def choose_best_hook(hook_a: str, hook_b: str):
    """
    Chooses best hook based on historical performance.
    """

    memory = load_hook_memory()

    a = memory.get(hook_a)
    b = memory.get(hook_b)

    if not a and not b:
        return hook_a  # default

    if a and not b:
        return hook_a

    if b and not a:
        return hook_b

    return hook_a if a["avg_completion"] >= b["avg_completion"] else hook_b
