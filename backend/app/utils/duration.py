import re


def parse_int(value) -> int:
    """JS parseInt: leading integer part, else NaN (treated as 0 here)."""
    m = re.match(r"\s*([+-]?\d+)", str(value if value is not None else ""))
    return int(m.group(1)) if m else 0


def convert_seconds_to_duration(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = (total_seconds % 3600) % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"
