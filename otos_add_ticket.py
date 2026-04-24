"""
Add Ötöslottó tickets (5/90) to lotto.db — random or manually entered.

Ötöslottó draws every Saturday.

Usage:
    python otos_add_ticket.py
"""

import random
import sqlite3
import os
from datetime import date, datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(__file__), "lotto.db")


def next_saturday() -> date:
    """Return the date of the next Saturday (never today)."""
    today = date.today()
    days_ahead = 5 - today.weekday()  # Saturday = weekday 5
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def next_n_saturdays(n: int) -> list[date]:
    """Return the next n Saturday draw dates."""
    first = next_saturday()
    return [first + timedelta(weeks=i) for i in range(n)]


def ensure_table(conn: sqlite3.Connection):
    """Create the tickets_otos table if it doesn't exist yet."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets_otos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,   -- ISO datetime, when the ticket was generated
            next_draw  TEXT NOT NULL,   -- ISO date, the Saturday this ticket is for
            num1       INTEGER NOT NULL,
            num2       INTEGER NOT NULL,
            num3       INTEGER NOT NULL,
            num4       INTEGER NOT NULL,
            num5       INTEGER NOT NULL
        )
    """)
    conn.commit()


def save_ticket(conn: sqlite3.Connection, numbers: list[int], draw_date: date):
    created_at = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO tickets_otos (created_at, next_draw, num1, num2, num3, num4, num5) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (created_at, draw_date.isoformat(), *numbers),
    )


def enter_numbers_manually() -> list[int]:
    while True:
        raw = input("Enter 5 numbers (1–90), space-separated: ").strip()
        parts = raw.split()
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            print("  Please enter integers only.")
            continue
        if len(nums) != 5:
            print(f"  Need exactly 5 numbers, got {len(nums)}.")
            continue
        if any(n < 1 or n > 90 for n in nums):
            print("  All numbers must be between 1 and 90.")
            continue
        if len(set(nums)) != 5:
            print("  Numbers must be unique.")
            continue
        return sorted(nums)


def main():
    conn = sqlite3.connect(DB_FILE)
    ensure_table(conn)

    while True:
        print("\n  g - Generate random numbers")
        print("  m - Enter numbers manually")
        print("  q - Quit")
        mode = input("Choice: ").strip().lower()

        if mode == "q":
            break
        elif mode == "m":
            numbers = enter_numbers_manually()
            print(f"  Manual:    {numbers}")
        else:
            numbers = sorted(random.sample(range(1, 91), 5))
            print(f"\n  Generated: {numbers}")

        print("  1 - Drop")
        print("  2 - Keep for next draw  ", next_saturday())
        print("  3 - Keep for next 5 draws")

        while True:
            choice = input("Choice: ").strip().lower()
            if choice in ("1", "2", "3"):
                break
            print("  Please enter 1, 2 or 3.")

        if choice == "1":
            print("  Dropped.")
        elif choice == "2":
            draw = next_saturday()
            save_ticket(conn, numbers, draw)
            conn.commit()
            print(f"  Saved for {draw}.")
        elif choice == "3":
            draws = next_n_saturdays(5)
            for draw in draws:
                save_ticket(conn, numbers, draw)
            conn.commit()
            print(f"  Saved for {len(draws)} draws: {draws[0]} through {draws[-1]}.")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
