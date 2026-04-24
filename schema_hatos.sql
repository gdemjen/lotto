CREATE TABLE IF NOT EXISTS draws_hatos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    year        INTEGER NOT NULL,
    week        INTEGER NOT NULL,
    day_of_week TEXT,               -- Hungarian weekday name, e.g. 'Csütörtök'
    draw_date   TEXT,               -- ISO format YYYY-MM-DD, NULL for pre-2001 rows
    jackpot     INTEGER NOT NULL DEFAULT 0,  -- 1 = jackpot won, 0 = rolled over
    jackpot_amt INTEGER NOT NULL DEFAULT 0,  -- in Ft
    w6          INTEGER NOT NULL DEFAULT 0,  -- 6-match winner count
    prize6      INTEGER NOT NULL DEFAULT 0,  -- 6-match prize per winner in Ft
    w5          INTEGER NOT NULL DEFAULT 0,
    prize5      INTEGER NOT NULL DEFAULT 0,
    w4          INTEGER NOT NULL DEFAULT 0,
    prize4      INTEGER NOT NULL DEFAULT 0,
    w3          INTEGER NOT NULL DEFAULT 0,
    prize3      INTEGER NOT NULL DEFAULT 0,
    num1        INTEGER NOT NULL,
    num2        INTEGER NOT NULL,
    num3        INTEGER NOT NULL,
    num4        INTEGER NOT NULL,
    num5        INTEGER NOT NULL,
    num6        INTEGER NOT NULL,
    bonus       INTEGER             -- pótszám, present only in pre-~2000 rows, NULL otherwise
);

-- Individual indexes on each number column for OR-based containment queries
CREATE INDEX IF NOT EXISTS idx_hatos_num1 ON draws_hatos(num1);
CREATE INDEX IF NOT EXISTS idx_hatos_num2 ON draws_hatos(num2);
CREATE INDEX IF NOT EXISTS idx_hatos_num3 ON draws_hatos(num3);
CREATE INDEX IF NOT EXISTS idx_hatos_num4 ON draws_hatos(num4);
CREATE INDEX IF NOT EXISTS idx_hatos_num5 ON draws_hatos(num5);
CREATE INDEX IF NOT EXISTS idx_hatos_num6 ON draws_hatos(num6);

-- Index for prize/jackpot range queries
CREATE INDEX IF NOT EXISTS idx_hatos_jackpot_amt ON draws_hatos(jackpot_amt);
CREATE INDEX IF NOT EXISTS idx_hatos_prize6      ON draws_hatos(prize6);

-- Index for year/week lookups
CREATE INDEX IF NOT EXISTS idx_hatos_year_week ON draws_hatos(year, week);
