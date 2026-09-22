"""SQLite: historial de conversación, pedidos y deduplicación de mensajes."""
import json
import sqlite3
import threading
from datetime import datetime

import config

_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _lock, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY, phone TEXT, role TEXT, content TEXT, ts TEXT);
            CREATE TABLE IF NOT EXISTS processed(wamid TEXT PRIMARY KEY, ts TEXT);
            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY, phone TEXT, name TEXT, address TEXT,
                items TEXT, total REAL, notes TEXT, status TEXT, ts TEXT);
            CREATE INDEX IF NOT EXISTS idx_msg_phone ON messages(phone, id);
            """
        )


def already_processed(wamid: str) -> bool:
    """Devuelve True si ya vimos este mensaje (Meta reintenta webhooks)."""
    with _lock, _conn() as c:
        try:
            c.execute("INSERT INTO processed VALUES(?,?)", (wamid, datetime.now().isoformat()))
            return False
        except sqlite3.IntegrityError:
            return True


def add_message(phone, role, content):
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO messages(phone, role, content, ts) VALUES(?,?,?,?)",
            (phone, role, content, datetime.now().isoformat()),
        )


def history(phone, limit):
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE phone=? ORDER BY id DESC LIMIT ?",
            (phone, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def reset(phone):
    with _lock, _conn() as c:
        c.execute("DELETE FROM messages WHERE phone=?", (phone,))


def create_order(phone, name, address, items, total, notes):
    with _lock, _conn() as c:
        cur = c.execute(
            "INSERT INTO orders(phone,name,address,items,total,notes,status,ts) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (phone, name, address, json.dumps(items, ensure_ascii=False), total, notes,
             "nuevo", datetime.now().isoformat()),
        )
        return cur.lastrowid


def list_orders(status=None):
    with _lock, _conn() as c:
        q = "SELECT * FROM orders" + (" WHERE status=?" if status else "") + " ORDER BY id DESC LIMIT 100"
        rows = c.execute(q, (status,) if status else ()).fetchall()
    return [dict(r) for r in rows]
