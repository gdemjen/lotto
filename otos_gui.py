"""
Tkinter GUI for Ötöslottó ticket management.

Two tabs:
  • My Tickets  — view saved tickets, add new ones (random or manual), delete
  • Recent Draws — last DRAW_LIMIT draws with numbers and all prize tiers

Usage:
    python otos_gui.py
"""

import random
import sqlite3
import os
import threading
import urllib.request
import importlib
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta

# Path to the shared SQLite database (same folder as this script)
DB_FILE = os.path.join(os.path.dirname(__file__), "lotto.db")

# How many recent draws to show in the Recent Draws tab
DRAW_LIMIT = 20


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def next_saturday() -> date:
    """Return the date of the next Saturday (skips today even if today is Saturday)."""
    today = date.today()
    days_ahead = 5 - today.weekday()   # Saturday = weekday index 5
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def next_n_saturdays(n: int) -> list[date]:
    """Return a list of the next n Saturday draw dates starting from next_saturday()."""
    first = next_saturday()
    return [first + timedelta(weeks=i) for i in range(n)]


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def ensure_table(conn: sqlite3.Connection):
    """Create tickets_otos if it does not yet exist (safe to call on every startup)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets_otos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,   -- ISO datetime, when the ticket was saved
            next_draw  TEXT NOT NULL,   -- ISO date of the target Saturday draw
            num1       INTEGER NOT NULL,
            num2       INTEGER NOT NULL,
            num3       INTEGER NOT NULL,
            num4       INTEGER NOT NULL,
            num5       INTEGER NOT NULL
        )
    """)
    conn.commit()


def save_ticket(conn: sqlite3.Connection, numbers: list[int], draw_date: date):
    """Insert one ticket row into tickets_otos and commit immediately."""
    conn.execute(
        "INSERT INTO tickets_otos (created_at, next_draw, num1, num2, num3, num4, num5) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
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


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class OtosApp(tk.Tk):
    """Main Tkinter window for the Ötöslottó ticket tool."""

    def __init__(self):
        super().__init__()
        self.title("Ötöslottó")
        self.geometry("860x540")
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
        nb.add(tab_tickets, text="  Megjátszott számaim  ")
        self._build_tickets_tab(tab_tickets)

        # Tab 2: read-only table showing the most recent DRAW_LIMIT draws
        tab_draws = ttk.Frame(nb, padding=8)
        nb.add(tab_draws, text="  Legutóbbi húzások  ")
        self._build_table_tab(
            tab_draws,
            cols=[
                ("draw_date", "Húzás dátuma", 100),
                ("numbers",   "Számok",        185),
                ("j_cnt",     "5 találat",      55),
                ("j_prize",   "Nyeremény 5",   130),
                ("h4_cnt",    "4 találat",      55),
                ("h4_prize",  "Nyeremény 4",   130),
                ("h3_cnt",    "3 találat",      55),
                ("h3_prize",  "Nyeremény 3",   130),
                ("h2_cnt",    "2 találat",      55),
                ("h2_prize",  "Nyeremény 2",   130),
            ],
            attr="tree_draws",
        )
        # Bind resize event so columns always fill the available width
        self.tree_draws.bind("<Configure>", self._resize_draws_columns)

        # Download button + status label below the draws table
        frm_dl = ttk.Frame(tab_draws)
        frm_dl.pack(fill=tk.X, pady=(6, 0))
        self.btn_refresh = ttk.Button(
            frm_dl, text="Adatok frissítése", command=self._start_download
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=(0, 10))
        self.lbl_dl_status = ttk.Label(frm_dl, text="")
        self.lbl_dl_status.pack(side=tk.LEFT)

        # Tab 3: statistics + ad-hoc SQL
        tab_stats = ttk.Frame(nb, padding=8)
        nb.add(tab_stats, text="  Elemzések  ")
        self._build_stats_tab(tab_stats)

    # Preset analyses for the Elemzések tab: name → SQL
    PRESET_ANALYSES = {
        "Leggyakoribb számok": """
            SELECT n AS Szám, COUNT(*) AS Előfordulás
            FROM (
                SELECT num1 AS n FROM draws_otos UNION ALL
                SELECT num2 FROM draws_otos UNION ALL
                SELECT num3 FROM draws_otos UNION ALL
                SELECT num4 FROM draws_otos UNION ALL
                SELECT num5 FROM draws_otos
            )
            GROUP BY n ORDER BY Előfordulás DESC
        """,
        "Legritkább számok": """
            SELECT n AS Szám, COUNT(*) AS Előfordulás
            FROM (
                SELECT num1 AS n FROM draws_otos UNION ALL
                SELECT num2 FROM draws_otos UNION ALL
                SELECT num3 FROM draws_otos UNION ALL
                SELECT num4 FROM draws_otos UNION ALL
                SELECT num5 FROM draws_otos
            )
            GROUP BY n ORDER BY Előfordulás ASC
        """,
        "Legnagyobb jackpotok (top 20)": """
            SELECT draw_date AS Dátum,
                   num1||'  '||num2||'  '||num3||'  '||num4||'  '||num5 AS Számok,
                   prize5 AS "Nyeremény (Ft)", w5 AS Nyerők
            FROM draws_otos
            WHERE prize5 > 0
            ORDER BY prize5 DESC
            LIMIT 20
        """,
        "Saját szelvények – találatok (≥ 3/5)": """
            SELECT * FROM (
                SELECT
                    t.next_draw AS Célhúzás,
                    t.num1||'  '||t.num2||'  '||t.num3||'  '||t.num4||'  '||t.num5 AS Szelvény,
                    d.draw_date AS Húzás,
                    d.num1||'  '||d.num2||'  '||d.num3||'  '||d.num4||'  '||d.num5 AS Kihúzottak,
                    (CASE WHEN d.num1=t.num1 OR d.num2=t.num1 OR d.num3=t.num1 OR d.num4=t.num1 OR d.num5=t.num1 THEN 1 ELSE 0 END)+
                    (CASE WHEN d.num1=t.num2 OR d.num2=t.num2 OR d.num3=t.num2 OR d.num4=t.num2 OR d.num5=t.num2 THEN 1 ELSE 0 END)+
                    (CASE WHEN d.num1=t.num3 OR d.num2=t.num3 OR d.num3=t.num3 OR d.num4=t.num3 OR d.num5=t.num3 THEN 1 ELSE 0 END)+
                    (CASE WHEN d.num1=t.num4 OR d.num2=t.num4 OR d.num3=t.num4 OR d.num4=t.num4 OR d.num5=t.num4 THEN 1 ELSE 0 END)+
                    (CASE WHEN d.num1=t.num5 OR d.num2=t.num5 OR d.num3=t.num5 OR d.num4=t.num5 OR d.num5=t.num5 THEN 1 ELSE 0 END) AS Találat
                FROM tickets_otos t CROSS JOIN draws_otos d
                WHERE d.draw_date IS NOT NULL
            ) WHERE Találat >= 3
            ORDER BY Találat DESC, Célhúzás
        """,
        "Legszűkebb húzás (legkisebb max)": """
            SELECT draw_date AS Dátum,
                   num1||'  '||num2||'  '||num3||'  '||num4||'  '||num5 AS Számok,
                   num5 AS "Legnagyobb szám"
            FROM draws_otos
            WHERE draw_date IS NOT NULL
            ORDER BY num5 ASC
            LIMIT 20
        """,
        "Legmagasabb húzás (legnagyobb min)": """
            SELECT draw_date AS Dátum,
                   num1||'  '||num2||'  '||num3||'  '||num4||'  '||num5 AS Számok,
                   num1 AS "Legkisebb szám"
            FROM draws_otos
            WHERE draw_date IS NOT NULL
            ORDER BY num1 DESC
            LIMIT 20
        """,
    }

    _SQL_DEFAULT = (
        "SELECT draw_date, num1, num2, num3, num4, num5, prize5\n"
        "FROM draws_otos\n"
        "WHERE prize5 > 0\n"
        "ORDER BY prize5 DESC\n"
        "LIMIT 10"
    )

    # Parallel lists used by _resize_draws_columns — must match col order above
    _DRAWS_COLS    = ["draw_date", "numbers",
                      "j_cnt", "j_prize", "h4_cnt", "h4_prize",
                      "h3_cnt", "h3_prize", "h2_cnt", "h2_prize"]
    # Relative widths; larger = wider column. Sum = 99.
    _DRAWS_WEIGHTS = [9, 18, 5, 13, 5, 13, 5, 13, 5, 13]

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
            ("next_draw",  "Húzás dátuma",  110),
            ("numbers",    "Számok",         190),
            ("created_at", "Mentés ideje",   160),
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
        ttk.Button(frm_del, text="Kijelölt törlése", command=self.delete_ticket).pack(side=tk.LEFT)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(10, 6))

        # --- lower section: add-ticket controls ---

        # Large display showing the current numbers (or "—" when none selected)
        frm_disp = ttk.LabelFrame(parent, text="Számok", padding=(16, 6))
        frm_disp.pack(fill=tk.X, pady=(0, 8))
        self.lbl_numbers = ttk.Label(
            frm_disp, text="—", font=("Courier New", 22, "bold"), anchor="center"
        )
        self.lbl_numbers.pack(fill=tk.X)

        # Generate button and manual-entry field on the same row
        frm_row = ttk.Frame(parent)
        frm_row.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(frm_row, text="Generálás", command=self.generate_numbers).pack(
            side=tk.LEFT, padx=(0, 12)
        )

        frm_manual = ttk.LabelFrame(frm_row, text="Kézi megadás", padding=(6, 4))
        frm_manual.pack(side=tk.LEFT)
        self.entry_manual = ttk.Entry(frm_manual, font=("Courier New", 12), width=22)
        self.entry_manual.pack(side=tk.LEFT, padx=(0, 6))
        # Allow submitting manual entry with the Enter key
        self.entry_manual.bind("<Return>", lambda _: self.set_manual())
        ttk.Button(frm_manual, text="Beállít", command=self.set_manual).pack(side=tk.LEFT)

        # Save buttons — disabled until numbers are set
        frm_save = ttk.Frame(parent)
        frm_save.pack(fill=tk.X, pady=(0, 4))

        self.btn_next = ttk.Button(
            frm_save,
            text=f"Mentés következő húzásra  ({next_saturday()})",
            command=self.keep_next,
            state=tk.DISABLED,
        )
        self.btn_next.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_five = ttk.Button(
            frm_save,
            text="Mentés következő 5 húzásra",
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
            tree.column(col_id, width=width, minwidth=40)

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
        """Pick 5 unique random numbers from 1–90 and display them."""
        self.numbers = sorted(random.sample(range(1, 91), 5))
        self._show_numbers("Generated")

    def set_manual(self):
        """
        Read and validate the manual-entry field.
        Accepts space-separated integers; must be exactly 5 unique values in 1–90.
        """
        raw = self.entry_manual.get().strip()
        parts = raw.split()
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            messagebox.showerror("Hibás bevitel", "Kérjük, csak egész számokat adjon meg.")
            return
        if len(nums) != 5:
            messagebox.showerror("Hibás bevitel", f"Pontosan 5 számot kell megadni, {len(nums)} lett megadva.")
            return
        if any(n < 1 or n > 90 for n in nums):
            messagebox.showerror("Hibás bevitel", "Minden szám 1 és 90 közé kell essen.")
            return
        if len(set(nums)) != 5:
            messagebox.showerror("Hibás bevitel", "A számok egyediek kell legyenek.")
            return
        self.numbers = sorted(nums)
        self._show_numbers("Kézzel megadva")

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
        """Save the current numbers for the next Saturday draw only."""
        draw = next_saturday()
        save_ticket(self.conn, self.numbers, draw)
        self.lbl_status.config(text=f"Saved for {draw}.")
        self._disable_save_buttons()
        self.refresh_tickets()

    def keep_five(self):
        """Save the current numbers for each of the next 5 Saturday draws."""
        draws = next_n_saturdays(5)
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
        self.conn.execute("DELETE FROM tickets_otos WHERE id = ?", (row_id,))
        self.conn.commit()
        self.refresh_tickets()

    # -----------------------------------------------------------------------
    # Data refresh — reload from DB into the UI
    # -----------------------------------------------------------------------

    def refresh_tickets(self):
        """
        Reload all rows from tickets_otos into the My Tickets table.
        Tickets whose draw date has already passed are rendered in grey.
        """
        self.tree_tickets.delete(*self.tree_tickets.get_children())
        cur = self.conn.execute(
            "SELECT id, next_draw, num1, num2, num3, num4, num5, created_at "
            "FROM tickets_otos ORDER BY next_draw ASC, id ASC"
        )
        today = date.today().isoformat()
        for row_id, next_draw, n1, n2, n3, n4, n5, created_at in cur:
            iid = self.tree_tickets.insert(
                "", tk.END,
                values=(next_draw, fmt_nums(n1, n2, n3, n4, n5), created_at),
                tags=(str(row_id),),   # tag carries the DB id for deletion
            )
            # Grey out past tickets so upcoming draws stand out
            if next_draw < today:
                self.tree_tickets.item(iid, tags=(str(row_id), "past"))
        self.tree_tickets.tag_configure("past", foreground="#999999")

    def refresh_draws(self):
        """
        Load the most recent DRAW_LIMIT draws from draws_otos into the Recent Draws table.
        Silently skips if the table does not yet exist (import not run yet).
        """
        self.tree_draws.delete(*self.tree_draws.get_children())
        try:
            cur = self.conn.execute(
                "SELECT draw_date, num1, num2, num3, num4, num5, "
                "       w5, prize5, w4, prize4, w3, prize3, w2, prize2 "
                "FROM draws_otos "
                "WHERE draw_date IS NOT NULL "
                "ORDER BY draw_date DESC "
                f"LIMIT {DRAW_LIMIT}"
            )
            for draw_date, n1, n2, n3, n4, n5, w5, p5, w4, p4, w3, p3, w2, p2 in cur:
                self.tree_draws.insert(
                    "", tk.END,
                    values=(
                        draw_date,
                        fmt_nums(n1, n2, n3, n4, n5),
                        w5 or "—", fmt_prize(p5),   # 5-hit (jackpot) winners + prize
                        w4 or "—", fmt_prize(p4),   # 4-hit winners + prize
                        w3 or "—", fmt_prize(p3),   # 3-hit winners + prize
                        w2 or "—", fmt_prize(p2),   # 2-hit winners + prize
                    ),
                )
        except sqlite3.OperationalError:
            pass    # draws_otos not yet imported — table simply shows empty

    # -----------------------------------------------------------------------
    # Statistics tab
    # -----------------------------------------------------------------------

    def _build_stats_tab(self, parent):
        paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # --- upper pane: preset analyses ---
        frm_top = ttk.Frame(paned, padding=4)
        paned.add(frm_top, weight=2)

        frm_combo = ttk.Frame(frm_top)
        frm_combo.pack(fill=tk.X, pady=(0, 6))
        self.combo_preset = ttk.Combobox(
            frm_combo, values=list(self.PRESET_ANALYSES.keys()),
            state="readonly", width=42,
        )
        self.combo_preset.current(0)
        self.combo_preset.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(frm_combo, text="Megjelenítés", command=self._run_preset).pack(side=tk.LEFT)

        frm_ptree = ttk.Frame(frm_top)
        frm_ptree.pack(fill=tk.BOTH, expand=True)
        self.tree_preset = ttk.Treeview(frm_ptree, show="headings", selectmode="browse")
        vsb_p = ttk.Scrollbar(frm_ptree, orient=tk.VERTICAL, command=self.tree_preset.yview)
        hsb_p = ttk.Scrollbar(frm_ptree, orient=tk.HORIZONTAL, command=self.tree_preset.xview)
        self.tree_preset.configure(yscrollcommand=vsb_p.set, xscrollcommand=hsb_p.set)
        self.tree_preset.grid(row=0, column=0, sticky="nsew")
        vsb_p.grid(row=0, column=1, sticky="ns")
        hsb_p.grid(row=1, column=0, sticky="ew")
        frm_ptree.rowconfigure(0, weight=1)
        frm_ptree.columnconfigure(0, weight=1)

        # --- lower pane: ad-hoc SQL ---
        frm_bot = ttk.Frame(paned, padding=4)
        paned.add(frm_bot, weight=1)

        ttk.Label(frm_bot, text="Ad-hoc SQL lekérdezés:").pack(anchor="w")

        frm_editor = ttk.Frame(frm_bot)
        frm_editor.pack(fill=tk.X, pady=(2, 4))
        self.txt_sql = tk.Text(
            frm_editor, height=4, font=("Courier New", 10), wrap=tk.NONE
        )
        vsb_sql = ttk.Scrollbar(frm_editor, orient=tk.VERTICAL, command=self.txt_sql.yview)
        self.txt_sql.configure(yscrollcommand=vsb_sql.set)
        self.txt_sql.pack(side=tk.LEFT, fill=tk.X, expand=True)
        vsb_sql.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_sql.insert("1.0", self._SQL_DEFAULT)

        frm_sql_ctrl = ttk.Frame(frm_bot)
        frm_sql_ctrl.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(
            frm_sql_ctrl, text="Lekérdezés futtatása", command=self._run_sql
        ).pack(side=tk.LEFT, padx=(0, 10))
        self.lbl_sql_status = ttk.Label(frm_sql_ctrl, text="")
        self.lbl_sql_status.pack(side=tk.LEFT)

        frm_stree = ttk.Frame(frm_bot)
        frm_stree.pack(fill=tk.BOTH, expand=True)
        self.tree_sql_result = ttk.Treeview(frm_stree, show="headings", selectmode="browse")
        vsb_s = ttk.Scrollbar(frm_stree, orient=tk.VERTICAL, command=self.tree_sql_result.yview)
        hsb_s = ttk.Scrollbar(frm_stree, orient=tk.HORIZONTAL, command=self.tree_sql_result.xview)
        self.tree_sql_result.configure(yscrollcommand=vsb_s.set, xscrollcommand=hsb_s.set)
        self.tree_sql_result.grid(row=0, column=0, sticky="nsew")
        vsb_s.grid(row=0, column=1, sticky="ns")
        hsb_s.grid(row=1, column=0, sticky="ew")
        frm_stree.rowconfigure(0, weight=1)
        frm_stree.columnconfigure(0, weight=1)

    def _populate_tree(self, tree, cursor):
        cols = [d[0] for d in cursor.description]
        tree.configure(columns=cols)
        avail = max(400, tree.winfo_width() - 20)
        col_w = max(60, avail // len(cols))
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_w, minwidth=40)
        tree.delete(*tree.get_children())
        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row)

    def _run_preset(self):
        name = self.combo_preset.get()
        sql = self.PRESET_ANALYSES.get(name)
        if not sql:
            return
        try:
            cur = self.conn.execute(sql)
            self._populate_tree(self.tree_preset, cur)
        except sqlite3.OperationalError as exc:
            self.tree_preset.configure(columns=["hiba"])
            self.tree_preset.heading("hiba", text="Hiba")
            self.tree_preset.column("hiba", width=500)
            self.tree_preset.delete(*self.tree_preset.get_children())
            self.tree_preset.insert("", tk.END, values=(str(exc),))

    def _run_sql(self):
        sql = self.txt_sql.get("1.0", tk.END).strip()
        if not sql:
            return
        try:
            cur = self.conn.execute(sql)
            if cur.description:
                self._populate_tree(self.tree_sql_result, cur)
                n = len(self.tree_sql_result.get_children())
                self.lbl_sql_status.config(text=f"{n} sor.", foreground="#2a7a2a")
            else:
                self.tree_sql_result.delete(*self.tree_sql_result.get_children())
                self.lbl_sql_status.config(
                    text="Kész (nincs visszatérési érték).", foreground="#2a7a2a"
                )
        except Exception as exc:
            self.tree_sql_result.delete(*self.tree_sql_result.get_children())
            self.lbl_sql_status.config(text=f"Hiba: {exc}", foreground="#cc0000")

    # -----------------------------------------------------------------------
    # Download & refresh
    # -----------------------------------------------------------------------

    def _start_download(self):
        """Kick off the CSV download + reimport in a background thread."""
        self.btn_refresh.config(state=tk.DISABLED)
        self.lbl_dl_status.config(text="Letöltés folyamatban...", foreground="#555555")
        threading.Thread(target=self._do_download, daemon=True).start()

    def _do_download(self):
        try:
            url = "https://bet.szerencsejatek.hu/cmsfiles/otos.csv"
            dest = os.path.join(os.path.dirname(__file__), "otos.csv")
            urllib.request.urlretrieve(url, dest)
            mod = importlib.import_module("import_otos")
            importlib.reload(mod)
            mod.main()
            self.after(0, self._on_download_done, None)
        except Exception as exc:
            self.after(0, self._on_download_done, str(exc))

    def _on_download_done(self, error: str | None):
        self.btn_refresh.config(state=tk.NORMAL)
        if error:
            self.lbl_dl_status.config(text=f"Hiba: {error}", foreground="#cc0000")
        else:
            self.refresh_draws()
            self.lbl_dl_status.config(text="Frissítve.", foreground="#2a7a2a")

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------

    def destroy(self):
        """Close the DB connection cleanly before the window is destroyed."""
        self.conn.close()
        super().destroy()


if __name__ == "__main__":
    app = OtosApp()
    app.mainloop()
