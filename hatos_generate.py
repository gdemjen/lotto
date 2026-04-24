"""
Generate Hatoslottó tickets (6/45) and save them to lotto.db.

Hatoslottó draws every Thursday and Sunday.

Usage:
    python hatos_generate.py
"""

import random
import sqlite3
import os
from datetime import date, datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(__file__), "lotto.db")


def next_draw_date() -> date:
    """Return the date of the next Hatoslottó draw (Thursday or Sunday, never today)."""
    today = date.today()

    def days_to(weekday: int) -> int:
        ahead = weekday - today.weekday()
        return ahead if ahead > 0 else ahead + 7

    return today + timedelta(days=min(days_to(3), days_to(6)))  # 3=Thu, 6=Sun


def next_n_draws(n: int) -> list[date]:
    """Return the next n Hatoslottó draw dates (alternating Thu/Sun)."""
    draws = []
    d = next_draw_date()
    for _ in range(n):
        draws.append(d)
        # Advance to next Thu or Sun strictly after d
        days_to_thu = (3 - d.weekday()) % 7 or 7
        days_to_sun = (6 - d.weekday()) % 7 or 7
        d = d + timedelta(days=min(days_to_thu, days_to_sun))
    return draws


def ensure_table(conn: sqlite3.Connection):
    """Create the tickets_hatos table if it doesn't exist yet."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets_hatos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,   -- ISO datetime, when the ticket was generated
            next_draw  TEXT NOT NULL,   -- ISO date, the draw this ticket is for
            num1       INTEGER NOT NULL,
            num2       INTEGER NOT NULL,
            num3       INTEGER NOT NULL,
            num4       INTEGER NOT NULL,
            num5       INTEGER NOT NULL,
            num6       INTEGER NOT NULL
        )
    """)
    conn.commit()


def save_ticket(conn: sqlite3.Connection, numbers: list[int], draw_date: date):
    created_at = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO tickets_hatos (created_at, next_draw, num1, num2, num3, num4, num5, num6) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (created_at, draw_date.isoformat(), *numbers),
    )


def main():
    conn = sqlite3.connect(DB_FILE)
    ensure_table(conn)

    while True:
        # Generate 6 unique numbers from 1-45 in ascending order
        numbers = sorted(random.sample(range(1, 46), 6))
        print(f"\nGenerated: {numbers}")

        # Ask what to do with these numbers
        print("  1 - Drop")
        print("  2 - Keep for next draw  ", next_draw_date())
        print("  3 - Keep for next 5 draws")
        print("  q - Quit")

        while True:
            choice = input("Choice: ").strip().lower()
            if choice in ("1", "2", "3", "q"):
                break
            print("  Please enter 1, 2, 3 or q.")

        if choice == "q":
            break
        elif choice == "1":
            print("  Dropped.")
        elif choice == "2":
            draw = next_draw_date()
            save_ticket(conn, numbers, draw)
            conn.commit()
            print(f"  Saved for {draw}.")
        elif choice == "3":
            draws = next_n_draws(5)
            for draw in draws:
                save_ticket(conn, numbers, draw)
            conn.commit()
            print(f"  Saved for {len(draws)} draws: {draws[0]} through {draws[-1]}.")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
