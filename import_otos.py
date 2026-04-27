"""
Import otos.csv (Ötöslottó, 5/90) into lotto.db as table draws_otos.

Usage:
    python import_otos.py

Safe to re-run: drops and recreates draws_otos each time.
"""

import sqlite3
import os
from utils import parse_amount, parse_date

CSV_FILE = os.path.join(os.path.dirname(__file__), "otos.csv")
DB_FILE  = os.path.join(os.path.dirname(__file__), "lotto.db")


def load_csv(path: str) -> list[tuple]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line:
                continue
            cols = line.split(";")
            if len(cols) != 16:
                continue  # skip malformed rows

            year        = int(cols[0].strip())
            week        = int(cols[1].strip())
            draw_date   = parse_date(cols[2])
            w5          = int(cols[3].strip())   # jackpot winners (5/5)
            prize5      = parse_amount(cols[4])   # jackpot prize
            w4          = int(cols[5].strip())   # 4-match winners
            prize4      = parse_amount(cols[6])
            w3          = int(cols[7].strip())   # 3-match winners
            prize3      = parse_amount(cols[8])
            w2          = int(cols[9].strip())   # 2-match winners
            prize2      = parse_amount(cols[10])
            num1        = int(cols[11].strip())
            num2        = int(cols[12].strip())
            num3        = int(cols[13].strip())
            num4        = int(cols[14].strip())
            num5        = int(cols[15].strip())

            rows.append((
                year, week, draw_date,
                num1, num2, num3, num4, num5,
                w5, prize5, w4, prize4, w3, prize3, w2, prize2,
            ))
    return rows


def main():
    print(f"Reading {CSV_FILE} ...")
    rows = load_csv(CSV_FILE)
    print(f"  Parsed {len(rows)} rows")

    print(f"Writing {DB_FILE} ...")
    conn = sqlite3.connect(DB_FILE)

    schema_path = os.path.join(os.path.dirname(__file__), "schema_otos.sql")
    conn.execute("DROP TABLE IF EXISTS draws_otos")
    with open(schema_path) as f:
        conn.executescript(f.read())

    conn.executemany(
        """
        INSERT INTO draws_otos
            (year, week, draw_date,
             num1, num2, num3, num4, num5,
             w5, prize5, w4, prize4, w3, prize3, w2, prize2)
        VALUES (?,?,?, ?,?,?,?,?, ?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    conn.commit()

    # Quick verification
    total  = conn.execute("SELECT COUNT(*) FROM draws_otos").fetchone()[0]
    w_date = conn.execute("SELECT COUNT(*) FROM draws_otos WHERE draw_date IS NOT NULL").fetchone()[0]

    latest = conn.execute(
        "SELECT draw_date, num1, num2, num3, num4, num5 FROM draws_otos "
        "WHERE draw_date IS NOT NULL ORDER BY draw_date DESC LIMIT 1"
    ).fetchone()

    last_jp = conn.execute(
        "SELECT draw_date, w5, prize5, num1, num2, num3, num4, num5 FROM draws_otos "
        "WHERE w5 > 0 AND draw_date IS NOT NULL ORDER BY draw_date DESC LIMIT 1"
    ).fetchone()

    print(f"\nVerification:")
    print(f"  Total rows    : {total}")
    print(f"  Rows with date: {w_date}")
    if latest:
        nums = "  ".join(f"{n:02d}" for n in latest[1:])
        print(f"  Latest draw   : {latest[0]}  →  {nums}")
    if last_jp:
        date, winners, prize, *nums = last_jp
        nums_str = "  ".join(f"{n:02d}" for n in nums)
        print(f"  Last jackpot  : {date}  ({winners} winner(s), {prize:,} Ft)  →  {nums_str}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
