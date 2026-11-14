"""Firmware version parsing and comparison."""


def parse_version(text: str) -> tuple[int, int, int]:
    """Turn '1.4.2' into (1, 4, 2). Raises ValueError on bad input."""
    parts = text.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"expected MAJOR.MINOR.PATCH, got {text!r}")
    try:
        major, minor, patch = (int(p) for p in parts)
    except ValueError:
        raise ValueError(f"non-numeric version part in {text!r}") from None
    if min(major, minor, patch) < 0:
        raise ValueError(f"negative version part in {text!r}")
    return major, minor, patch


def is_newer(candidate: str, installed: str) -> bool:
    return parse_version(candidate) > parse_version(installed)
