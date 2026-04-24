"""
Check if a set of 5 numbers was ever drawn in the Hungarian Ötöslottó.

Usage:
    python check_numbers.py
"""

import sqlite3
import os

# lotto.db sits next to this script, created by import_sqlite.py
DB_FILE = os.path.join(os.path.dirname(__file__), "lotto.db")


def get_numbers() -> list[int]:
    """Prompt the user for 5 distinct numbers in the range 1-90."""
    print("Enter 5 numbers (1-90), one per line:")
    numbers = []
    while len(numbers) < 5:
        raw = input(f"  Number {len(numbers) + 1}: ").strip()
        try:
            n = int(raw)
        except ValueError:
            print("  Not a valid number, try again.")
            continue
        if not 1 <= n <= 90:
            print("  Must be between 1 and 90, try again.")
            continue
        if n in numbers:
            print("  Already entered, try again.")
            continue
        numbers.append(n)
    return sorted(numbers)


def check(conn: sqlite3.Connection, numbers: list[int]) -> list[tuple]:
    """Return all draws where every one of the given numbers appeared.

    The drawn numbers are stored in five separate columns (num1-num5), so we
    check each input number against all five columns with OR, then AND the
    five conditions together.  Example for [7, 23, 45]:
        WHERE (num1=7  OR num2=7  OR ... OR num5=7)
          AND (num1=23 OR num2=23 OR ... OR num5=23)
          AND (num1=45 OR num2=45 OR ... OR num5=45)
    Each column has an index, so SQLite can resolve the OR conditions quickly.
    """
    def col_in(n):
        # Build the condition that checks whether n appears in any number column
        return f"(num1={n} OR num2={n} OR num3={n} OR num4={n} OR num5={n})"

    # Join all per-number conditions with AND so every number must be present
    where = " AND ".join(col_in(n) for n in numbers)

    return conn.execute(f"""
        SELECT year, week, draw_date, num1, num2, num3, num4, num5
        FROM draws
        WHERE {where}
        ORDER BY year, week
    """).fetchall()


def main():
    conn = sqlite3.connect(DB_FILE)

    numbers = get_numbers()
    print(f"\nChecking for draw containing: {numbers} ...")

    hits = check(conn, numbers)

    if not hits:
        print("These 5 numbers were never drawn together.")
    else:
        print(f"Found {len(hits)} matching draw(s):\n")
        # Header row with fixed-width columns for readability
        print(f"  {'Year':<6} {'Week':<6} {'Date':<12} {'Numbers'}")
        print(f"  {'-'*4:<6} {'-'*4:<6} {'-'*10:<12} {'-'*20}")
        for year, week, date, *nums in hits:
            # draw_date is NULL for pre-2005 rows
            date_str = date if date else "unknown"
            print(f"  {year:<6} {week:<6} {date_str:<12} {nums}")

    conn.close()


if __name__ == "__main__":
    main()
