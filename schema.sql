CREATE TABLE IF NOT EXISTS draws (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    year        INTEGER NOT NULL,
    week        INTEGER NOT NULL,
    draw_date   TEXT,               -- ISO format YYYY-MM-DD, NULL for pre-2005 rows
    jackpot     INTEGER NOT NULL DEFAULT 0,  -- 1 = jackpot won, 0 = rolled over
    jackpot_amt INTEGER NOT NULL DEFAULT 0,  -- in Ft, e.g. 6780926220
    w5          INTEGER NOT NULL DEFAULT 0,  -- 5-match winner count
    prize5      INTEGER NOT NULL DEFAULT 0,  -- 5-match prize per winner in Ft
    w4          INTEGER NOT NULL DEFAULT 0,
    prize4      INTEGER NOT NULL DEFAULT 0,
    w3          INTEGER NOT NULL DEFAULT 0,
    prize3      INTEGER NOT NULL DEFAULT 0,
    num1        INTEGER NOT NULL,
    num2        INTEGER NOT NULL,
    num3        INTEGER NOT NULL,
    num4        INTEGER NOT NULL,
    num5        INTEGER NOT NULL
);

-- Individual indexes on each number column for OR-based containment queries
CREATE INDEX IF NOT EXISTS idx_num1 ON draws(num1);
CREATE INDEX IF NOT EXISTS idx_num2 ON draws(num2);
CREATE INDEX IF NOT EXISTS idx_num3 ON draws(num3);
CREATE INDEX IF NOT EXISTS idx_num4 ON draws(num4);
CREATE INDEX IF NOT EXISTS idx_num5 ON draws(num5);

-- Index for prize/jackpot range queries
CREATE INDEX IF NOT EXISTS idx_jackpot_amt ON draws(jackpot_amt);
CREATE INDEX IF NOT EXISTS idx_prize5      ON draws(prize5);

-- Index for year/week lookups
CREATE INDEX IF NOT EXISTS idx_year_week ON draws(year, week);
