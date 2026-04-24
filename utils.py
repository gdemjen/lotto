"""
Shared parsing utilities used by both import_otos.py and import_hatos.py.
"""


def parse_amount(raw: str) -> int:
    """Convert a Hungarian currency string to an integer.

    Examples:
        '6 780 926 220 Ft' -> 6780926220
        '0 Ft'             -> 0
        '0'                -> 0  (bare zero, appears in recent hatos.csv rows)
    """
    digits = "".join(c for c in raw if c.isdigit())
    return int(digits) if digits else 0


def parse_date(raw: str) -> str | None:
    """Convert Hungarian date format to ISO format.

    '2026.04.18.' -> '2026-04-18'
    ''            -> None  (empty in pre-2001/2005 rows)
    """
    raw = raw.strip().rstrip(".")
    if not raw:
        return None
    parts = raw.split(".")
    if len(parts) == 3:
        return f"{parts[0]}-{parts[1]}-{parts[2]}"
    return None
