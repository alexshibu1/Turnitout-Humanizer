import re

_ZERO_WIDTH_PATTERN = re.compile(
    "[​‌‍⁠﻿­‎‏]"
)


def purge_zero_width(text: str) -> tuple[str, int]:
    cleaned, count = _ZERO_WIDTH_PATTERN.subn("", text)
    return cleaned, count
