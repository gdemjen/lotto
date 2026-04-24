"""
Check if a set of 6 numbers was ever drawn in the Hungarian Hatoslottó (6/45).

Usage:
    python check_hatos.py
"""

import sqlite3
import os

# lotto.db sits next to this script, created by import_hatos.py
DB_FILE = os.path.join(os.path.dirname(__file__), "lotto.db")


def get_numbers() -> list[int]:
    """Prompt the user for 6 distinct numbers in the range 1-45."""
    print("Hatoslottó (6/45) — Enter 6 numbers (1-45), one per line:")
    numbers = []
    while len(numbers) < 6:
        raw = input(f"  Number {len(numbers) + 1}: ").strip()
        try:
            n = int(raw)
        except ValueError:
            print("  Not a valid number, try again.")
            continue
        if not 1 <= n <= 45:
            print("  Must be between 1 and 45, try again.")
            continue
        if n in numbers:
            print("  Already entered, try again.")
            continue
        numbers.append(n)
    return sorted(numbers)


def check(conn: sqlite3.Connection, numbers: list[int]) -> list[tuple]:
    """Return all draws where every one of the given numbers appeared.

    The drawn numbers are stored in six separate columns (num1-num6), so we
    check each input number against all six columns with OR, then AND the
    six conditions together.
    Each column has an index, so SQLite can resolve the OR conditions quickly.
    """
    def col_in(n):
        # Build the condition that checks whether n appears in any number column
        return f"(num1={n} OR num2={n} OR num3={n} OR num4={n} OR num5={n} OR num6={n})"

    # Join all per-number conditions with AND so every number must be present
    where = " AND ".join(col_in(n) for n in numbers)

    return conn.execute(f"""
        SELECT year, week, day_of_week, draw_date, num1, num2, num3, num4, num5, num6
        FROM draws_hatos
        WHERE {where}
        ORDER BY year, week
    """).fetchall()


def main():
    conn = sqlite3.connect(DB_FILE)

    numbers = get_numbers()
    print(f"\nChecking for draw containing: {numbers} ...")

    hits = check(conn, numbers)

    if not hits:
        print("These 6 numbers were never drawn together.")
    else:
        print(f"Found {len(hits)} matching draw(s):\n")
        # Header row with fixed-width columns for readability
        print(f"  {'Year':<6} {'Week':<6} {'Day':<12} {'Date':<12} {'Numbers'}")
        print(f"  {'-'*4:<6} {'-'*4:<6} {'-'*10:<12} {'-'*10:<12} {'-'*25}")
        for year, week, day, date, *nums in hits:
            # draw_date is NULL for pre-2001 rows
            date_str = date if date else "unknown"
            print(f"  {year:<6} {week:<6} {day:<12} {date_str:<12} {nums}")

    conn.close()


if __name__ == "__main__":
    main()
