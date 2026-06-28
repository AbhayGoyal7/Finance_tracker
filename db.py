import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS txns (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       TEXT NOT NULL,
                category   TEXT NOT NULL,
                amount     REAL NOT NULL,
                note       TEXT,
                type       TEXT NOT NULL DEFAULT 'expense',
                chat_id    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id    TEXT PRIMARY KEY,
                name       TEXT,
                token      TEXT UNIQUE,
                joined_at  TEXT NOT NULL
            )
        """)


def get_or_create_user(chat_id, name=""):
    chat_id = str(chat_id)
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,)).fetchone()
        if row:
            return dict(row)
        token = hashlib.sha256(f"{chat_id}-secret-salt-xk92".encode()).hexdigest()[:16]
        con.execute(
            "INSERT INTO users (chat_id, name, token, joined_at) VALUES (?,?,?,?)",
            (chat_id, name, token, datetime.utcnow().isoformat())
        )
        return {"chat_id": chat_id, "name": name, "token": token}


def get_user_by_token(token):
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE token=?", (token,)).fetchone()
        return dict(row) if row else None


def add(date, category, amount, note, type_, chat_id):
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO txns (date, category, amount, note, type, chat_id, created_at) VALUES (?,?,?,?,?,?,?)",
            (date, category, amount, note, type_, str(chat_id), datetime.utcnow().isoformat())
        )
        return cur.lastrowid


def undo_last(chat_id):
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM txns WHERE chat_id=? ORDER BY id DESC LIMIT 1",
            (str(chat_id),)
        ).fetchone()
        if row is None:
            return None
        deleted = dict(row)
        con.execute("DELETE FROM txns WHERE id=?", (row["id"],))
        return deleted


def user_rows(chat_id):
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM txns WHERE chat_id=? ORDER BY id DESC",
            (str(chat_id),)
        ).fetchall()
        return [dict(r) for r in rows]


def user_month_total(chat_id, month):
    with _conn() as con:
        rows = con.execute(
            "SELECT type, SUM(amount) as total FROM txns WHERE chat_id=? AND date LIKE ? GROUP BY type",
            (str(chat_id), f"{month}-%")
        ).fetchall()
    income, expense = 0.0, 0.0
    for r in rows:
        if r["type"] == "income":
            income += r["total"]
        else:
            expense += r["total"]
    return {"income": income, "expense": expense, "net": income - expense}


def user_month_cats(chat_id, month):
    with _conn() as con:
        rows = con.execute(
            "SELECT category, SUM(amount) as total FROM txns WHERE chat_id=? AND date LIKE ? AND type='expense' GROUP BY category ORDER BY total DESC",
            (str(chat_id), f"{month}-%")
        ).fetchall()
        return [dict(r) for r in rows]


init_db()