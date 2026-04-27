# Hungarian Lottery Analyzer

A local Python toolkit for working with historical Hungarian lottery data. It downloads official draw results, stores them in a SQLite database, lets you generate random tickets, and checks your saved tickets against real draw outcomes.

Two games are supported:

| Game | Hungarian name | Pick | Range | Draw schedule |
|---|---|---|---|---|
| Ötöslottó | 5/90 | 5 numbers | 1–90 | Every Saturday |
| Hatoslottó | 6/45 | 6 numbers | 1–45 | Every Thursday and Sunday |

---

## Requirements

- Python 3.10 or later (uses `str | None` union type hints)
- No third-party packages — everything uses the Python standard library

---

## Quick Start

```bash
# 1. Download the latest draw data and populate the database
python download_data.py

# 2. Add tickets (GUI or CLI)
python otos_gui.py          # Ötöslottó — graphical interface
python otos_add_ticket.py   # Ötöslottó — command-line
python hatos_generate.py    # Hatoslottó — command-line

# 3. After the draw — check your tickets
python otos_check_tickets.py
python hatos_check_tickets.py
```

---

## Project Structure

```
lotto/
├── download_data.py          # Download CSVs + re-import into DB
├── import_otos.py            # Import otos.csv → draws_otos table
├── import_hatos.py           # Import hatos.csv → draws_hatos table
├── utils.py                  # Shared CSV parsing helpers
├── otos_gui.py               # Tkinter GUI — add & view Ötöslottó tickets
├── otos_add_ticket.py        # CLI — add Ötöslottó tickets (random or manual)
├── hatos_generate.py         # CLI — generate & save Hatoslottó tickets
├── otos_check_tickets.py     # Check saved Ötöslottó tickets for wins
├── hatos_check_tickets.py    # Check saved Hatoslottó tickets for wins
├── check_otos.py             # Look up any 5 numbers in draw history
├── check_hatos.py            # Look up any 6 numbers in draw history
├── schema_otos.sql           # DDL for draws_otos table + indexes
├── schema_hatos.sql          # DDL for draws_hatos table + indexes
├── otos.csv                  # Raw draw data — Ötöslottó
├── hatos.csv                 # Raw draw data — Hatoslottó
└── lotto.db                  # SQLite database (all tables)
```

> **Obsolete files** (kept for reference, safe to delete):
> `schema.sql`, `import_sqlite.py`, `check_numbers.py`

---

## Data Sources

The CSV files are published by Szerencsejáték Zrt. (the official Hungarian lottery operator):

| File | URL |
|---|---|
| otos.csv | https://bet.szerencsejatek.hu/cmsfiles/otos.csv |
| hatos.csv | https://bet.szerencsejatek.hu/cmsfiles/hatos.csv |

Both files are semicolon-delimited, UTF-8 with BOM, no header row, newest draw first.

---

## Scripts in Detail

### `download_data.py`

Downloads the latest versions of both CSV files from the official source and immediately re-imports them into `lotto.db`. Uses only Python's built-in `urllib` — no extra packages needed.

```bash
python download_data.py
```

Run this regularly (e.g. after each draw) to keep the database up to date before checking tickets.

---

### `import_otos.py` / `import_hatos.py`

Parse the respective CSV file and load all rows into the database. Both scripts are safe to re-run: they drop and recreate their table on each execution, so the database always reflects the current CSV exactly.

```bash
python import_otos.py
python import_hatos.py
```

Each script prints a short verification summary after import:

```
Verification:
  Total rows    : 3607
  Rows with date: 3200
  Latest draw   : 2026-04-25  →  22  23  65  78  80
  Last jackpot  : 2026-04-18  (1 winner(s), 6 780 926 220 Ft)  →  09  23  45  71  84
```

> **Note:** `download_data.py` already calls both import scripts automatically, so you only need to run these manually if you have updated a CSV file by hand.

---

### `utils.py`

Shared helper functions used by both import scripts. Not intended to be run directly.

- `parse_amount("6 780 926 220 Ft")` → `6780926220` — strips Hungarian thousand-separator spaces and the `Ft` suffix, returns an integer
- `parse_date("2026.04.18.")` → `"2026-04-18"` — converts to ISO format; returns `None` for empty strings (pre-2001/2005 rows have no date)

---

### `otos_gui.py`

Graphical interface for Ötöslottó ticket management. No extra packages required — uses Python's built-in `tkinter`.

```bash
python otos_gui.py
```

**My Tickets tab** — shows all saved tickets (upcoming draws highlighted, past draws greyed out). Below the list: generate random numbers or type them manually, then save for the next draw or the next 5 draws. Individual tickets can be deleted.

**Recent Draws tab** — shows the last 20 draws with drawn numbers and winner counts + prize amounts for all four prize tiers (5 / 4 / 3 / 2 hits). Columns resize automatically to fill the window.

---

### `otos_add_ticket.py`

Command-line alternative to `otos_gui.py`. Each iteration offers a choice of generating random numbers or entering them manually, then asks what to do:

```
  g - Generate random numbers
  m - Enter numbers manually
  q - Quit
Choice: g

  Generated: [8, 11, 23, 57, 71]
  1 - Drop
  2 - Keep for next draw   2026-05-03
  3 - Keep for next 5 draws
Choice:
```

| Option | Action |
|---|---|
| `1` | Discard the numbers — nothing is saved |
| `2` | Save one row to `tickets_otos` for the next Saturday |
| `3` | Save 5 rows to `tickets_otos`, one for each of the next 5 Saturdays |
| `q` | Exit |

```bash
python otos_add_ticket.py
```

---

### `hatos_generate.py`

Works identically to `otos_generate.py` but for Hatoslottó: generates 6 unique numbers from 1–45 and saves to `tickets_hatos`.

Because Hatoslottó draws twice a week (Thursday and Sunday), option `2` saves for the next upcoming draw day (whichever of Thursday/Sunday comes first), and option `3` saves for the next 5 draw dates, alternating Thursday and Sunday.

```bash
python hatos_generate.py
```

---

### `otos_check_tickets.py`

Checks all saved Ötöslottó tickets whose draw date has already passed. Joins `tickets_otos` with `draws_otos` on the draw date and counts how many of your numbers matched the official result.

```bash
python otos_check_tickets.py
```

**Prize tiers:**

| Matches | Prize |
|---|---|
| 5 | 1st prize (Jackpot) |
| 4 | 2nd prize |
| 3 | 3rd prize |
| 2 | 4th prize |

**Example output:**

```
Checked 3 ticket(s).  Prizes found: 1

ID    Draw date    Ticket                    Drawn                     Matches              Result
--------------------------------------------------------------------------------------------------------------
1     2026-04-26   [8, 11, 23, 57, 71]       [3, 11, 23, 45, 71]       [11, 23, 71]         3rd prize
2     2026-04-26   [14, 38, 46, 55, 82]      [3, 11, 23, 45, 71]       []                   0 match(es)
3     2026-04-26   [25, 61, 67, 76, 81]      [3, 11, 23, 45, 71]       []                   0 match(es)

*** 1 winning ticket(s) found! ***
```

Tickets whose draw date is still in the future are silently skipped — run `download_data.py` first to make sure the latest draws are in the database.

---

### `hatos_check_tickets.py`

Same as `otos_check_tickets.py` but for Hatoslottó. Joins `tickets_hatos` with `draws_hatos`. The output also shows the day of the week for each draw (Thursday or Sunday).

```bash
python hatos_check_tickets.py
```

**Prize tiers:**

| Matches | Prize |
|---|---|
| 6 | 1st prize (Jackpot) |
| 5 | 2nd prize |
| 4 | 3rd prize |
| 3 | 4th prize |

---

### `check_otos.py`

Historical lookup tool — not related to saved tickets. Enter any 5 numbers and it searches the entire Ötöslottó draw history (1957–present) to find draws where all 5 appeared together.

```bash
python check_otos.py
```

```
Ötöslottó (5/90) — Enter 5 numbers (1-90), one per line:
  Number 1: 9
  Number 2: 23
  ...

Checking for draw containing: [9, 23, 45, 71, 84] ...
Found 1 matching draw(s):

  Year   Week   Date         Numbers
  ----   ----   ----------   --------------------
  2026   16     2026-04-18   [9, 23, 45, 71, 84]
```

Input is validated: numbers outside 1–90 or duplicates are rejected with a prompt to retry.

---

### `check_hatos.py`

Same as `check_otos.py` but for Hatoslottó: enter 6 numbers in the range 1–45 and search the full draw history (1988–present). Results also show the day of the week for each matching draw.

```bash
python check_hatos.py
```

---

## Database

All data is stored in `lotto.db`, a single SQLite file in the project folder. It contains four tables:

### `draws_otos`

Historical Ötöslottó results. 3,607 rows spanning 1957–present.

| Column | Type | Description |
|---|---|---|
| `year` | INTEGER | Draw year |
| `week` | INTEGER | Week number |
| `draw_date` | TEXT | ISO date (NULL for pre-2005 rows) |
| `num1`–`num5` | INTEGER | The 5 drawn numbers, in ascending order |
| `w5` / `prize5` | INTEGER | Jackpot (5-match) winner count / prize per winner in Ft |
| `w4` / `prize4` | INTEGER | 4-match winner count / prize per winner in Ft |
| `w3` / `prize3` | INTEGER | 3-match winner count / prize per winner in Ft |
| `w2` / `prize2` | INTEGER | 2-match winner count / prize per winner in Ft |

### `draws_hatos`

Historical Hatoslottó results. 1,806 rows spanning 1988–present.

| Column | Type | Description |
|---|---|---|
| `year` | INTEGER | Draw year |
| `week` | INTEGER | Week number |
| `day_of_week` | TEXT | Hungarian weekday name (`Csütörtök` / `Vasárnap`) |
| `draw_date` | TEXT | ISO date (NULL for pre-2001 rows) |
| `jackpot` | INTEGER | 1 = jackpot won, 0 = rolled over |
| `jackpot_amt` | INTEGER | Jackpot pool in Ft |
| `w6` / `prize6` | INTEGER | 6-match winner count / prize per winner in Ft |
| `w5` / `prize5` | INTEGER | 5-match winner count / prize per winner in Ft |
| `w4` / `prize4` | INTEGER | 4-match winner count / prize per winner in Ft |
| `w3` / `prize3` | INTEGER | 3-match winner count / prize per winner in Ft |
| `num1`–`num6` | INTEGER | The 6 drawn numbers, stored in ascending order |
| `bonus` | INTEGER | Bonus ball (pótszám), present only in pre-~2000 rows |

### `tickets_otos`

Your generated Ötöslottó tickets.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `created_at` | TEXT | ISO datetime when the ticket was generated |
| `next_draw` | TEXT | ISO date of the draw this ticket is for |
| `num1`–`num5` | INTEGER | Your 5 chosen numbers |

### `tickets_hatos`

Your generated Hatoslottó tickets.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `created_at` | TEXT | ISO datetime when the ticket was generated |
| `next_draw` | TEXT | ISO date of the draw this ticket is for |
| `num1`–`num6` | INTEGER | Your 6 chosen numbers |

---

## Typical Workflow

```
Every week:

1.  python download_data.py          ← fetch latest draws, update DB

2.  python otos_check_tickets.py     ← did any saved tickets win?
    python hatos_check_tickets.py

3.  python otos_gui.py               ← add new Ötöslottó tickets (GUI)
    python hatos_generate.py         ← add new Hatoslottó tickets (CLI)
```

---

## Example SQL Queries

The following `.sql` files are included for use in a GUI tool such as [DB Browser for SQLite](https://sqlitebrowser.org):

**Draw with the highest lowest number drawn (Ötöslottó):**
```sql
SELECT year, week, draw_date, num1, num2, num3, num4, num5
FROM draws_otos
ORDER BY num1 DESC
LIMIT 1;
```

**Most frequently drawn number:**
```sql
SELECT number, COUNT(*) AS times_drawn
FROM (
    SELECT num1 AS number FROM draws_otos UNION ALL
    SELECT num2 FROM draws_otos UNION ALL
    SELECT num3 FROM draws_otos UNION ALL
    SELECT num4 FROM draws_otos UNION ALL
    SELECT num5 FROM draws_otos
)
GROUP BY number
ORDER BY times_drawn DESC
LIMIT 1;
```

**All jackpots over 1 billion Ft:**
```sql
SELECT year, week, draw_date, w5 AS winners, prize5 AS jackpot_prize
FROM draws_otos
WHERE prize5 > 1000000000
ORDER BY prize5 DESC;
```

For Hatoslottó queries, replace `draws_otos` with `draws_hatos` and extend number columns to include `num6`.
