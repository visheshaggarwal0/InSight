"""complaint_extraction.py
Standalone complaint extraction utility for InSight ML pipeline.

PROVISIONAL: This is a heuristic keyword/discourse-marker regex.
It has NOT been validated against manually labelled ground truth.
Detection rate and precision/recall are unknown. Treat as an
indicative signal only, not a measured classifier output.

Returns a dictionary with:
  detected : bool   – True if a complaint pattern was found
  text     : str    – the matched span (empty string if not detected)
  start    : int    – start character offset (None if not detected)
  end      : int    – end character offset (None if not detected)
  trigger  : str    – always 'pattern' when detected, else None
"""

import re
from typing import Dict, Any

# Compiled once at import time.
# IMPORTANT: This is a raw string (r"...").
# \b = word-boundary, \s = whitespace – standard regex metacharacters.
# Do NOT double-escape them as \\b or \\s; that would make the pattern
# search for a literal backslash followed by 'b' or 's' and match nothing.
_PATTERN = re.compile(
    r"\b(?:but|however|except\s+that|except|although|unfortunately|until"
    r"|cracked|jammed|leaked|burning|stinging|rash|dermatitis"
    r"|crash|crashes|freeze|freezes|failed|fails|limbo|terrible|horrible)\b.*",
    re.IGNORECASE,
)


def extract_complaint_span(text: str) -> Dict[str, Any]:
    """Extract a complaint clause from *text* using a heuristic regex.

    The heuristic looks for discourse markers (e.g. 'but', 'however') or
    defect-related keywords (e.g. 'cracked', 'leaked'). When a match is
    found the span text, its character offsets relative to *text*, and a
    detection flag are returned. When no match is found ``detected`` is
    ``False`` and the offset fields are ``None``.

    The returned span satisfies::

        text[start:end] == span_text   # when detected is True

    This property is tested in tests/test_complaint_extraction.py.
    """
    if not isinstance(text, str):
        return {"detected": False, "text": "", "start": None, "end": None, "trigger": None}

    match = _PATTERN.search(text)
    if match:
        return {
            "detected": True,
            "text": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "trigger": "pattern",
        }
    return {
        "detected": False,
        "text": "",
        "start": None,
        "end": None,
        "trigger": None,
    }


__all__ = ["extract_complaint_span"]
