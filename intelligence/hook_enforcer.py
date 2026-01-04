def enforce_hook(script: str) -> str:
    """
    Ensures the first line is a strong hook.
    Regenerates structure if weak.
    """

    lines = [l.strip() for l in script.split("\n") if l.strip()]
    if not lines:
        return script

    first_line = lines[0].lower()

    weak_starts = (
        "this is", "this case", "in the year",
        "this story", "this crime"
    )

    if first_line.startswith(weak_starts):
        # Move context down
        new_lines = [
            "He was found dead — but the timeline made no sense.",
            lines[0]
        ] + lines[1:]
        return "\n".join(new_lines)

    return script
