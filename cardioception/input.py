"""Shared keyboard input helpers for PsychoPy tasks."""

from __future__ import annotations

import re
from typing import List, Optional

_NUMPAD_PREFIXES = ("num_", "num", "numpad_", "numpad", "kp_", "kp")


def digit_key_list(min_digit: int = 0, max_digit: int = 9) -> List[str]:
    """Return accepted key names for top-row and numpad digits."""
    if min_digit < 0 or max_digit > 9 or min_digit > max_digit:
        raise ValueError("min_digit and max_digit must satisfy 0 <= min <= max <= 9")

    key_list: List[str] = []
    for digit in range(min_digit, max_digit + 1):
        value = str(digit)
        key_list.append(value)
        for prefix in _NUMPAD_PREFIXES:
            key_list.append(f"{prefix}{value}")
    return key_list


def parse_digit_key(key: str) -> Optional[str]:
    """Extract a numeric character from a PsychoPy key name."""
    if not key:
        return None

    normalized = key.lower()
    if len(normalized) == 1 and normalized.isdigit():
        return normalized

    for prefix in _NUMPAD_PREFIXES:
        if normalized.startswith(prefix):
            suffix = normalized[len(prefix) :]
            if len(suffix) == 1 and suffix.isdigit():
                return suffix

    # Fallback for key names ending in a digit (e.g., "num_1", "numpad_1")
    match = re.search(r"(\d)$", normalized)
    if match:
        return match.group(1)

    return None
