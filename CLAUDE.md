# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hungarian lottery historical data project. Two games are supported, each with its own CSV, schema, importer, and checker script. All data lives in a single SQLite database (`lotto.db`).

| Game | CSV | Rows | Draw | Numbers | Range |
|---|---|---|---|---|---|
| Ötöslottó | `otos.csv` | 3,607 | Weekly | 5 | 1–90 |
| Hatoslottó | `hatos.csv` | 1,806 | Twice weekly (Thu + Sun) | 6 | 1–45 |

## Scripts

| Script | Purpose |
|---|---|
| `import_otos.py` | Parse otos.csv → `draws_otos` table in lotto.db |
| `import_hatos.py` | Parse hatos.csv → `draws_hatos` table in lotto.db |
| `check_otos.py` | Interactive: enter 5 numbers, find matching draws |
| `check_hatos.py` | Interactive: enter 6 numbers, find matching draws |
| `utils.py` | Shared helpers: `parse_amount()`, `parse_date()` |

Re-import after CSV updates:
```
python import_otos.py
python import_hatos.py
```

## Database: lotto.db

Single SQLite file with two tables. Both are dropped and recreated on each import run.

**`draws_otos`** columns: `year, week, draw_date, jackpot, jackpot_amt, w5, prize5, w4, prize4, w3, prize3, num1–num5`

**`draws_hatos`** columns: `year, week, day_of_week, draw_date, jackpot, jackpot_amt, w6, prize6, w5, prize5, w4, prize4, w3, prize3, num1–num6, bonus`
- `day_of_week`: Hungarian weekday name (e.g. `Csütörtök`, `Vasárnap`)
- `bonus`: pótszám (bonus ball), present only in pre-~2000 rows, NULL otherwise

Prize amounts are stored as plain integers in Ft (e.g. `6780926220`). Dates are ISO `YYYY-MM-DD` or NULL for older rows without date data.

## Data: otos.csv

Semicolon-delimited, UTF-8 with BOM, newest draw first. No header row. 16 columns:

`year ; week ; draw_date ; jackpot_flag ; jackpot_amt ; w5 ; prize5 ; w4 ; prize4 ; w3 ; prize3 ; num1 ; num2 ; num3 ; num4 ; num5`

- Pre-~2005 rows: date empty, all prize/winner fields are `0`
- Number columns occasionally have trailing spaces — always `.strip()` before parsing

## Data: hatos.csv

Semicolon-delimited, UTF-8 with BOM, newest draw first. No header row. 20 columns (recent) or 21 columns (pre-~2000, extra bonus number at end):

`year ; week ; day_of_week ; draw_date ; jackpot_flag ; jackpot_amt ; w6 ; prize6 ; w5 ; prize5 ; w4 ; prize4 ; w3 ; prize3 ; num1 ; num2 ; num3 ; num4 ; num5 ; num6 [; bonus]`

- Pre-~2001 rows: date empty, prize/winner fields are `0`
- `prize6` column shows bare `0` (not `0 Ft`) in recent rows — `parse_amount()` handles both

## Shared Parsing (utils.py)

```python
parse_amount("6 780 926 220 Ft")  # → 6780926220
parse_amount("0")                  # → 0
parse_date("2026.04.18.")          # → "2026-04-18"
parse_date("")                     # → None
```

## SQL Query Files

Ad-hoc queries saved in the project root:
- `highest_minimum.sql` — draw with highest lowest number
- `lowest_max.sql`
- `most_often_drawed.sql`

These target `draws_otos`. For `draws_hatos` queries, replace the table name and extend number columns to include `num6`.

## Obsolete Files

The following files predate the two-game refactor and can be deleted:
`schema.sql`, `import_sqlite.py`, `check_numbers.py`
