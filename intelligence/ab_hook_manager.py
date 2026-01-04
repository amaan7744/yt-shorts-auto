import random

def choose_hook(hook_a: str, hook_b: str, memory: dict = None):
    """
    Alternates hooks safely across runs.
    """

    if not memory:
        return hook_a if random.random() < 0.5 else hook_b

    a_score = memory.get("hook_a", 0)
    b_score = memory.get("hook_b", 0)

    return hook_a if a_score >= b_score else hook_b
