"""
Check saved Hatoslottó tickets against actual draw results.

Compares tickets in tickets_hatos with draws in draws_hatos where the draw
date has already passed. Reports match count and prize tier for each ticket.

Prize tiers (Hatoslottó):
    6 matches = 1st prize (jackpot)
    5 matches = 2nd prize
    4 matches = 3rd prize
    3 matches = 4th prize

Usage:
    python hatos_check_tickets.py
"""

import sqlite3
import os
from datetime import date

DB_FILE = os.path.join(os.path.dirname(__file__), "lotto.db")

PRIZE_TIER = {6: "1st prize (JACKPOT!)", 5: "2nd prize", 4: "3rd prize", 3: "4th prize"}


def check_tickets(conn: sqlite3.Connection) -> list[dict]:
    """Fetch all tickets whose draw date has passed and join with actual results."""
    today = date.today().isoformat()

    rows = conn.execute("""
        SELECT
            t.id, t.created_at, t.next_draw,
            t.num1, t.num2, t.num3, t.num4, t.num5, t.num6,
            d.num1, d.num2, d.num3, d.num4, d.num5, d.num6,
            d.day_of_week, d.jackpot_amt, d.prize6, d.prize5, d.prize4, d.prize3
        FROM tickets_hatos t
        JOIN draws_hatos d ON d.draw_date = t.next_draw
        WHERE t.next_draw <= ?
        ORDER BY t.next_draw, t.id
    """, (today,)).fetchall()

    results = []
    for row in rows:
        (tid, created_at, next_draw,
         t1, t2, t3, t4, t5, t6,
         d1, d2, d3, d4, d5, d6,
         day_of_week, jackpot_amt, prize6, prize5, prize4, prize3) = row

        ticket  = {t1, t2, t3, t4, t5, t6}
        drawn   = {d1, d2, d3, d4, d5, d6}
        matches = ticket & drawn
        n       = len(matches)

        # Look up the prize amount for this match count
        prize_amounts = {6: jackpot_amt, 5: prize5, 4: prize4, 3: prize3}
        prize_amt = prize_amounts.get(n, 0)

        results.append({
            "id":          tid,
            "created_at":  created_at,
            "draw_date":   next_draw,
            "day_of_week": day_of_week,
            "ticket":      sorted(ticket),
            "drawn":       sorted(drawn),
            "matches":     sorted(matches),
            "n":           n,
            "tier":        PRIZE_TIER.get(n),
            "prize_amt":   prize_amt,
        })
    return results


def main():
    conn = sqlite3.connect(DB_FILE)

    # Check that tickets_hatos exists
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tickets_hatos'"
    ).fetchone()
    if not exists:
        print("No tickets found — run hatos_generate.py first.")
        conn.close()
        return

    results = check_tickets(conn)
    conn.close()

    if not results:
        print("No tickets with a past draw date found.")
        return

    hits = [r for r in results if r["n"] >= 3]

    print(f"Checked {len(results)} ticket(s).  Prizes found: {len(hits)}\n")
    print(f"{'ID':<5} {'Draw date':<12} {'Day':<12} {'Ticket':<28} {'Drawn':<28} {'Matches':<22} {'Result'}")
    print("-" * 120)

    for r in results:
        tier_str  = r["tier"] if r["tier"] else f"{r['n']} match(es)"
        prize_str = f"  [{r['prize_amt']:,} Ft]" if r["prize_amt"] else ""
        print(
            f"{r['id']:<5} {r['draw_date']:<12} {r['day_of_week']:<12} "
            f"{str(r['ticket']):<28} {str(r['drawn']):<28} "
            f"{str(r['matches']):<22} {tier_str}{prize_str}"
        )

    if hits:
        print(f"\n*** {len(hits)} winning ticket(s) found! ***")


if __name__ == "__main__":
    main()
