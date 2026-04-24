"""
Import hatos.csv (Hatoslottó, 6/45) into lotto.db as table draws_hatos.

Usage:
    python import_hatos.py

Safe to re-run: drops and recreates draws_hatos each time.

CSV structure (semicolon-delimited, 20 or 21 columns):
  1  year
  2  week
  3  day_of_week  (Hungarian weekday name, e.g. 'Csütörtök')
  4  draw_date    (YYYY.MM.DD., empty for pre-2001 rows)
  5  jackpot      (0 or 1)
  6  jackpot_amt  (currency string)
  7  w6           (6-match winner count)
  8  prize6       (6-match prize per winner; bare '0' in recent rows, '0 Ft' in older)
  9  w5 / 10 prize5 / 11 w4 / 12 prize4 / 13 w3 / 14 prize3
  15-20  num1-num6
  21  bonus        (pótszám, present only in pre-~2000 rows)
"""

import sqlite3
import os
from utils import parse_amount, parse_date

CSV_FILE = os.path.join(os.path.dirname(__file__), "hatos.csv")
DB_FILE  = os.path.join(os.path.dirname(__file__), "lotto.db")


def load_csv(path: str) -> list[tuple]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line:
                continue
            cols = line.split(";")
            # Accept 20 columns (normal) or 21 (older rows with bonus number)
            if len(cols) not in (20, 21):
                continue

            year        = int(cols[0].strip())
            week        = int(cols[1].strip())
            day_of_week = cols[2].strip()
            draw_date   = parse_date(cols[3])
            jackpot     = int(cols[4].strip())
            jackpot_amt = parse_amount(cols[5])
            w6          = int(cols[6].strip())
            prize6      = parse_amount(cols[7])
            w5          = int(cols[8].strip())
            prize5      = parse_amount(cols[9])
            w4          = int(cols[10].strip())
            prize4      = parse_amount(cols[11])
            w3          = int(cols[12].strip())
            prize3      = parse_amount(cols[13])
            num1        = int(cols[14].strip())
            num2        = int(cols[15].strip())
            num3        = int(cols[16].strip())
            num4        = int(cols[17].strip())
            num5        = int(cols[18].strip())
            num6        = int(cols[19].strip())
            # Bonus number (pótszám) only present in older rows
            bonus       = int(cols[20].strip()) if len(cols) == 21 and cols[20].strip() else None

            rows.append((
                year, week, day_of_week, draw_date, jackpot, jackpot_amt,
                w6, prize6, w5, prize5, w4, prize4, w3, prize3,
                num1, num2, num3, num4, num5, num6, bonus,
            ))
    return rows


def main():
    print(f"Reading {CSV_FILE} ...")
    rows = load_csv(CSV_FILE)
    print(f"  Parsed {len(rows)} rows")

    print(f"Writing {DB_FILE} ...")
    conn = sqlite3.connect(DB_FILE)

    schema_path = os.path.join(os.path.dirname(__file__), "schema_hatos.sql")
    conn.execute("DROP TABLE IF EXISTS draws_hatos")
    with open(schema_path) as f:
        conn.executescript(f.read())

    conn.executemany(
        """
        INSERT INTO draws_hatos
            (year, week, day_of_week, draw_date, jackpot, jackpot_amt,
             w6, prize6, w5, prize5, w4, prize4, w3, prize3,
             num1, num2, num3, num4, num5, num6, bonus)
        VALUES (?,?,?,?,?,?, ?,?,?,?,?,?,?,?, ?,?,?,?,?,?,?)
        """,
        rows,
    )
    conn.commit()

    # Quick verification
    total  = conn.execute("SELECT COUNT(*) FROM draws_hatos").fetchone()[0]
    w_date = conn.execute("SELECT COUNT(*) FROM draws_hatos WHERE draw_date IS NOT NULL").fetchone()[0]
    w_bonus = conn.execute("SELECT COUNT(*) FROM draws_hatos WHERE bonus IS NOT NULL").fetchone()[0]
    max_jp = conn.execute("SELECT MAX(jackpot_amt) FROM draws_hatos").fetchone()[0]
    print(f"\nVerification:")
    print(f"  Total rows      : {total}")
    print(f"  Rows with date  : {w_date}")
    print(f"  Rows with bonus : {w_bonus}")
    print(f"  Biggest jackpot : {max_jp:,} Ft")

    # Spot-check: 2026 week 17 Thursday should be 9 14 19 20 36 40
    row = conn.execute(
        "SELECT num1,num2,num3,num4,num5,num6 FROM draws_hatos "
        "WHERE year=2026 AND week=17 AND day_of_week='Csütörtök'"
    ).fetchone()
    print(f"  2026-w17 Thu numbers: {row}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
