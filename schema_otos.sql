CREATE TABLE IF NOT EXISTS draws_otos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    year        INTEGER NOT NULL,
    week        INTEGER NOT NULL,
    draw_date   TEXT,               -- ISO format YYYY-MM-DD, NULL for pre-2005 rows
    num1        INTEGER NOT NULL,
    num2        INTEGER NOT NULL,
    num3        INTEGER NOT NULL,
    num4        INTEGER NOT NULL,
    num5        INTEGER NOT NULL,
    w5          INTEGER NOT NULL DEFAULT 0,  -- jackpot winners (all 5 correct)
    prize5      INTEGER NOT NULL DEFAULT 0,  -- jackpot prize per winner in Ft
    w4          INTEGER NOT NULL DEFAULT 0,  -- 4-match winners
    prize4      INTEGER NOT NULL DEFAULT 0,
    w3          INTEGER NOT NULL DEFAULT 0,  -- 3-match winners
    prize3      INTEGER NOT NULL DEFAULT 0,
    w2          INTEGER NOT NULL DEFAULT 0,  -- 2-match winners
    prize2      INTEGER NOT NULL DEFAULT 0
);

-- Individual indexes on each number column for OR-based containment queries
CREATE INDEX IF NOT EXISTS idx_otos_num1 ON draws_otos(num1);
CREATE INDEX IF NOT EXISTS idx_otos_num2 ON draws_otos(num2);
CREATE INDEX IF NOT EXISTS idx_otos_num3 ON draws_otos(num3);
CREATE INDEX IF NOT EXISTS idx_otos_num4 ON draws_otos(num4);
CREATE INDEX IF NOT EXISTS idx_otos_num5 ON draws_otos(num5);

-- Index for prize/jackpot range queries
CREATE INDEX IF NOT EXISTS idx_otos_prize5 ON draws_otos(prize5);
CREATE INDEX IF NOT EXISTS idx_otos_w5     ON draws_otos(w5);

-- Index for year/week lookups
CREATE INDEX IF NOT EXISTS idx_otos_year_week ON draws_otos(year, week);
