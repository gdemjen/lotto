"""
Tkinter GUI for Hatoslottó ticket management.

Hatoslottó is a 6/45 game: pick 6 numbers from 1–45.
Draws are held twice a week — every Thursday and Sunday.

Two tabs:
  • My Tickets   — view saved tickets, add new ones (random or manual), delete
  • Recent Draws — last DRAW_LIMIT draws with numbers and all four prize tiers

Usage:
    python hatos_gui.py
"""

import random
import sqlite3
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta

# Path to the shared SQLite database (same folder as this script)
DB_FILE = os.path.join(os.path.dirname(__file__), "lotto.db")

# How many recent draws to show in the Recent Draws tab
DRAW_LIMIT = 20


# ---------------------------------------------------------------------------
# Date helpers — Hatoslottó draws on Thursday (weekday 3) and Sunday (weekday 6)
# ---------------------------------------------------------------------------

def next_draw_date() -> date:
    """Return the date of the next Hatoslottó draw (Thu or Sun, never today)."""
    today = date.today()

    def days_to(weekday: int) -> int:
        ahead = weekday - today.weekday()
        return ahead if ahead > 0 else ahead + 7

    return today + timedelta(days=min(days_to(3), days_to(6)))


def next_n_draws(n: int) -> list[date]:
    """Return the next n Hatoslottó draw dates, alternating Thursday and Sunday."""
    draws = []
    d = next_draw_date()
    for _ in range(n):
        draws.append(d)
        # Advance strictly past d to the next Thu or Sun
        days_to_thu = (3 - d.weekday()) % 7 or 7
        days_to_sun = (6 - d.weekday()) % 7 or 7
        d = d + timedelta(days=min(days_to_thu, days_to_sun))
    return draws


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def ensure_table(conn: sqlite3.Connection):
    """Create tickets_hatos if it does not yet exist (safe to call on every startup)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets_hatos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,   -- ISO datetime, when the ticket was saved
            next_draw  TEXT NOT NULL,   -- ISO date of the target draw
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
    """Insert one ticket row into tickets_hatos and commit immediately."""
    conn.execute(
        "INSERT INTO tickets_hatos "
        "(created_at, next_draw, num1, num2, num3, num4, num5, num6) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), draw_date.isoformat(), *numbers),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_nums(*nums) -> str:
    """Format a sequence of lottery numbers as zero-padded, double-space-separated string."""
    return "  ".join(f"{n:02d}" for n in nums)


def fmt_prize(val) -> str:
    """Format an integer prize amount in Ft with Hungarian thousands separator, or '—' for zero."""
    if val is None or val == 0:
        return "—"
    return f"{val:,} Ft".replace(",", " ")


def fmt_day(raw: str | None) -> str:
    """Abbreviate the Hungarian weekday name stored in day_of_week to 4 characters."""
    if not raw:
        return "—"
    # 'Csütörtök' → 'Csüt', 'Vasárnap' → 'Vas.'
    return raw[:4].rstrip()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class HatosApp(tk.Tk):
    """Main Tkinter window for the Hatoslottó ticket tool."""

    def __init__(self):
        super().__init__()
        self.title("Hatoslottó")
        self.geometry("900x560")
        self.resizable(True, True)

        # Single persistent DB connection kept open for the lifetime of the app
        self.conn = sqlite3.connect(DB_FILE)
        ensure_table(self.conn)

        # Currently displayed/selected numbers (set by Generate or manual entry)
        self.numbers: list[int] = []

        self._build_ui()
        self.refresh_tickets()
        self.refresh_draws()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self):
        """Create the two-tab notebook and populate each tab."""
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: ticket list + add-ticket controls in a single view
        tab_tickets = ttk.Frame(nb, padding=8)
        nb.add(tab_tickets, text="  My Tickets  ")
        self._build_tickets_tab(tab_tickets)

        # Tab 2: read-only table of recent draws with prize info
        tab_draws = ttk.Frame(nb, padding=8)
        nb.add(tab_draws, text="  Recent Draws  ")
        self._build_table_tab(
            tab_draws,
            cols=[
                ("draw_date", "Draw Date", 100),
                ("day",       "Day",        50),   # Thu or Sun
                ("numbers",   "Numbers",   210),
                ("j_cnt",     "6 hits",     50),   # jackpot — all 6 correct
                ("j_prize",   "Prize 6",   120),
                ("h5_cnt",    "5 hits",     50),
                ("h5_prize",  "Prize 5",   120),
                ("h4_cnt",    "4 hits",     50),
                ("h4_prize",  "Prize 4",   120),
                ("h3_cnt",    "3 hits",     50),
                ("h3_prize",  "Prize 3",   120),
            ],
            attr="tree_draws",
        )
        # Bind resize event so columns always fill the available width
        self.tree_draws.bind("<Configure>", self._resize_draws_columns)

    # Parallel lists used by _resize_draws_columns — must match col order above
    _DRAWS_COLS = [
        "draw_date", "day", "numbers",
        "j_cnt", "j_prize",
        "h5_cnt", "h5_prize",
        "h4_cnt", "h4_prize",
        "h3_cnt", "h3_prize",
    ]
    # Relative widths; sum = 90
    _DRAWS_WEIGHTS = [8, 4, 16, 4, 11, 4, 11, 4, 11, 4, 11]

    def _resize_draws_columns(self, event):
        """Redistribute Recent Draws column widths proportionally on every resize."""
        w = event.width - 18    # subtract scrollbar width
        if w <= 0:
            return
        total = sum(self._DRAWS_WEIGHTS)
        for col, weight in zip(self._DRAWS_COLS, self._DRAWS_WEIGHTS):
            self.tree_draws.column(col, width=max(20, int(w * weight / total)))

    def _build_tickets_tab(self, parent):
        """
        Build the My Tickets tab layout:
          [top, expanding]  Treeview of saved tickets + Delete button
          [separator]
          [bottom, fixed]   Number display + Generate / Manual entry + Save buttons
        """
        # --- upper section: saved tickets ---
        frm_tree = ttk.Frame(parent)
        frm_tree.pack(fill=tk.BOTH, expand=True)

        cols = [
            ("next_draw",  "Draw Date",  110),
            ("numbers",    "Numbers",    220),
            ("created_at", "Saved At",   160),
        ]
        self.tree_tickets = ttk.Treeview(
            frm_tree, columns=[c[0] for c in cols], show="headings", selectmode="browse"
        )
        for col_id, heading, width in cols:
            self.tree_tickets.heading(col_id, text=heading)
            self.tree_tickets.column(col_id, width=width, minwidth=40)

        vsb = ttk.Scrollbar(frm_tree, orient=tk.VERTICAL, command=self.tree_tickets.yview)
        self.tree_tickets.configure(yscrollcommand=vsb.set)
        self.tree_tickets.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Delete button sits just below the table
        frm_del = ttk.Frame(parent)
        frm_del.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(frm_del, text="Delete selected", command=self.delete_ticket).pack(side=tk.LEFT)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(10, 6))

        # --- lower section: add-ticket controls ---

        # Large display showing the current numbers (or "—" when none selected)
        frm_disp = ttk.LabelFrame(parent, text="Numbers", padding=(16, 6))
        frm_disp.pack(fill=tk.X, pady=(0, 8))
        self.lbl_numbers = ttk.Label(
            frm_disp, text="—", font=("Courier New", 22, "bold"), anchor="center"
        )
        self.lbl_numbers.pack(fill=tk.X)

        # Generate button and manual-entry field on the same row
        frm_row = ttk.Frame(parent)
        frm_row.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(frm_row, text="Generate", command=self.generate_numbers).pack(
            side=tk.LEFT, padx=(0, 12)
        )

        frm_manual = ttk.LabelFrame(frm_row, text="Enter manually", padding=(6, 4))
        frm_manual.pack(side=tk.LEFT)
        self.entry_manual = ttk.Entry(frm_manual, font=("Courier New", 12), width=26)
        self.entry_manual.pack(side=tk.LEFT, padx=(0, 6))
        # Allow submitting manual entry with the Enter key
        self.entry_manual.bind("<Return>", lambda _: self.set_manual())
        ttk.Button(frm_manual, text="Set", command=self.set_manual).pack(side=tk.LEFT)

        # Save buttons — disabled until numbers are set
        frm_save = ttk.Frame(parent)
        frm_save.pack(fill=tk.X, pady=(0, 4))

        self.btn_next = ttk.Button(
            frm_save,
            text=f"Keep for next draw  ({next_draw_date()})",
            command=self.keep_next,
            state=tk.DISABLED,
        )
        self.btn_next.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_five = ttk.Button(
            frm_save,
            text="Keep for next 5 draws",
            command=self.keep_five,
            state=tk.DISABLED,
        )
        self.btn_five.pack(side=tk.LEFT)

        # Status line: shows "(Generated)", "(Manual)", or a save-confirmation message
        self.lbl_status = ttk.Label(parent, text="", foreground="#2a7a2a")
        self.lbl_status.pack(anchor="w")

    def _build_table_tab(self, parent, cols, attr, buttons=None):
        """
        Generic helper: create a Treeview with a vertical scrollbar.

        Args:
            parent:  The ttk.Frame that owns this table.
            cols:    List of (col_id, heading_text, initial_width) tuples.
            attr:    Name under which the Treeview is stored on self (e.g. "tree_draws").
            buttons: Optional list of (label, command) pairs added as buttons below the table.
        """
        frm = ttk.Frame(parent)
        frm.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(frm, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for col_id, heading, width in cols:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, minwidth=20)

        vsb = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Store the tree on self so action methods can reference it by name
        setattr(self, attr, tree)

        if buttons:
            frm_btns = ttk.Frame(parent)
            frm_btns.pack(fill=tk.X, pady=(6, 0))
            for label, cmd in buttons:
                ttk.Button(frm_btns, text=label, command=cmd).pack(side=tk.LEFT, padx=(0, 6))

    # -----------------------------------------------------------------------
    # Actions — number selection
    # -----------------------------------------------------------------------

    def generate_numbers(self):
        """Pick 6 unique random numbers from 1–45 and display them."""
        self.numbers = sorted(random.sample(range(1, 46), 6))
        self._show_numbers("Generated")

    def set_manual(self):
        """
        Read and validate the manual-entry field.
        Accepts space-separated integers; must be exactly 6 unique values in 1–45.
        """
        raw = self.entry_manual.get().strip()
        parts = raw.split()
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter integers only.")
            return
        if len(nums) != 6:
            messagebox.showerror("Invalid input", f"Need exactly 6 numbers, got {len(nums)}.")
            return
        if any(n < 1 or n > 45 for n in nums):
            messagebox.showerror("Invalid input", "All numbers must be between 1 and 45.")
            return
        if len(set(nums)) != 6:
            messagebox.showerror("Invalid input", "Numbers must be unique.")
            return
        self.numbers = sorted(nums)
        self._show_numbers("Manual")

    def _show_numbers(self, source: str):
        """Update the number display label and enable the save buttons."""
        self.lbl_numbers.config(text=fmt_nums(*self.numbers))
        self.btn_next.config(state=tk.NORMAL)
        self.btn_five.config(state=tk.NORMAL)
        self.lbl_status.config(text=f"({source})")

    # -----------------------------------------------------------------------
    # Actions — saving tickets
    # -----------------------------------------------------------------------

    def keep_next(self):
        """Save the current numbers for the next Thursday or Sunday draw."""
        draw = next_draw_date()
        save_ticket(self.conn, self.numbers, draw)
        self.lbl_status.config(text=f"Saved for {draw}.")
        self._disable_save_buttons()
        self.refresh_tickets()

    def keep_five(self):
        """Save the current numbers for each of the next 5 draw dates (Thu/Sun alternating)."""
        draws = next_n_draws(5)
        for draw in draws:
            save_ticket(self.conn, self.numbers, draw)
        self.lbl_status.config(text=f"Saved for {len(draws)} draws: {draws[0]} – {draws[-1]}.")
        self._disable_save_buttons()
        self.refresh_tickets()

    def _disable_save_buttons(self):
        """Disable save buttons after a ticket is saved (prevents accidental double-save)."""
        self.btn_next.config(state=tk.DISABLED)
        self.btn_five.config(state=tk.DISABLED)

    # -----------------------------------------------------------------------
    # Actions — deleting tickets
    # -----------------------------------------------------------------------

    def delete_ticket(self):
        """Delete the currently selected ticket row after user confirmation."""
        sel = self.tree_tickets.selection()
        if not sel:
            return
        # The DB row id is stored as the first tag on each Treeview item
        row_id = self.tree_tickets.item(sel[0], "tags")[0]
        if not messagebox.askyesno("Delete", "Delete the selected ticket?"):
            return
        self.conn.execute("DELETE FROM tickets_hatos WHERE id = ?", (row_id,))
        self.conn.commit()
        self.refresh_tickets()

    # -----------------------------------------------------------------------
    # Data refresh — reload from DB into the UI
    # -----------------------------------------------------------------------

    def refresh_tickets(self):
        """
        Reload all rows from tickets_hatos into the My Tickets table.
        Tickets whose draw date has already passed are rendered in grey.
        """
        self.tree_tickets.delete(*self.tree_tickets.get_children())
        cur = self.conn.execute(
            "SELECT id, next_draw, num1, num2, num3, num4, num5, num6, created_at "
            "FROM tickets_hatos ORDER BY next_draw ASC, id ASC"
        )
        today = date.today().isoformat()
        for row_id, next_draw, n1, n2, n3, n4, n5, n6, created_at in cur:
            iid = self.tree_tickets.insert(
                "", tk.END,
                values=(next_draw, fmt_nums(n1, n2, n3, n4, n5, n6), created_at),
                tags=(str(row_id),),   # tag carries the DB id for deletion
            )
            # Grey out past tickets so upcoming draws stand out
            if next_draw < today:
                self.tree_tickets.item(iid, tags=(str(row_id), "past"))
        self.tree_tickets.tag_configure("past", foreground="#999999")

    def refresh_draws(self):
        """
        Load the most recent DRAW_LIMIT draws from draws_hatos into the Recent Draws table.
        Shows day_of_week (Thu/Sun), numbers, and all four prize tiers.
        Silently skips if the table does not yet exist (import not run yet).

        Prize tier mapping for draws_hatos:
          6 hits — jackpot (flag 0/1) + jackpot_amt (prize)
          5 hits — w5 + prize5
          4 hits — w4 + prize4
          3 hits — w3 + prize3
        """
        self.tree_draws.delete(*self.tree_draws.get_children())
        try:
            cur = self.conn.execute(
                "SELECT draw_date, day_of_week, "
                "       num1, num2, num3, num4, num5, num6, "
                "       jackpot, jackpot_amt, w5, prize5, w4, prize4, w3, prize3 "
                "FROM draws_hatos "
                "WHERE draw_date IS NOT NULL "
                "ORDER BY draw_date DESC "
                f"LIMIT {DRAW_LIMIT}"
            )
            for (draw_date, day_of_week,
                 n1, n2, n3, n4, n5, n6,
                 jk, jk_amt, w5, p5, w4, p4, w3, p3) in cur:
                self.tree_draws.insert(
                    "", tk.END,
                    values=(
                        draw_date,
                        fmt_day(day_of_week),
                        fmt_nums(n1, n2, n3, n4, n5, n6),
                        jk or "—",  fmt_prize(jk_amt),   # 6-hit (jackpot) winner + prize
                        w5 or "—",  fmt_prize(p5),        # 5-hit winners + prize
                        w4 or "—",  fmt_prize(p4),        # 4-hit winners + prize
                        w3 or "—",  fmt_prize(p3),        # 3-hit winners + prize
                    ),
                )
        except sqlite3.OperationalError:
            pass    # draws_hatos not yet imported — table simply shows empty

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------

    def destroy(self):
        """Close the DB connection cleanly before the window is destroyed."""
        self.conn.close()
        super().destroy()


if __name__ == "__main__":
    app = HatosApp()
    app.mainloop()
