"""
filters.py — Text cleaning and construction-plan text filtering.
"""

from __future__ import annotations

import re


def clean_text(t: str) -> str:
    """Normalize OCR text: uppercase, collapse whitespace, strip punctuation."""
    t = t.strip().upper()
    t = re.sub(r"\s+", " ", t)
    t = t.strip(" '\"")
    if re.match(r".+[\/.\-]$", t) and not re.search(r"[A-Z0-9][\/.\-][A-Z0-9]$", t):
        t = t[:-1]
    return t.strip()


def is_construction_text(text: str) -> bool:
    """
    Return True if *text* looks like a meaningful construction-plan label.

    Matches:
    - Uppercase abbreviations (HVAC, CORRIDOR, etc.)
    - Short codes (UP, DN, TYP, RM, …)
    - Alphanumeric codes (A5.1, W9, etc.)
    - Dimensions (12'-6", 3/4", etc.)
    - Multi-word names if each word ≥3 chars and alphabetic
    """
    if not text:
        return False
    t = text.strip()
    if len(t) < 2:
        return False
    if not re.match(r"^[A-Za-z0-9.\"'\/()\s-]+$", t):
        return False

    patterns = [
        r"^[A-Z]{3,}$",
        r"^(UP|DN|NO|ID|LV|EL|TYP|RM)$",
        r"^[A-Z]+\d+[A-Z]?$",
        r"^[A-Z]+\d+(\.\d+)?$",
        r"^\d{2,4}$",
        r"^\d+(\.\d+)?[\"']?$",
        r"^\d+\/\d+[\"']?$",
    ]

    tokens = t.split()
    hit = False
    for tok in tokens:
        tok = tok.strip()
        if len(tok) < 2:
            continue
        for pat in patterns:
            if re.match(pat, tok):
                hit = True
                break
        if hit:
            break
    if hit:
        return True

    if all(len(tok) >= 3 and tok.isalpha() for tok in tokens):
        return True

    return False
