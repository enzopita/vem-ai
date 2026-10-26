import os
import sqlite3
from contextlib import closing
from pathlib import Path

from vemai.models import PushKeys, Subscription, SubscriptionIn

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    operator TEXT NOT NULL,
    stop_id TEXT NOT NULL,
    stop_name TEXT NOT NULL,
    line_id TEXT NOT NULL,
    line_label TEXT NOT NULL,
    time TEXT NOT NULL,
    lead_min INTEGER NOT NULL,
    UNIQUE (endpoint, operator, stop_id, line_id, time)
);
CREATE TABLE IF NOT EXISTS notifications (
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    vehicle TEXT NOT NULL,
    kind TEXT NOT NULL,
    day TEXT NOT NULL,
    UNIQUE (subscription_id, vehicle, kind, day)
);
"""


def _to_subscription(row: sqlite3.Row) -> Subscription:
    return Subscription(
        id=row["id"],
        endpoint=row["endpoint"],
        keys=PushKeys(p256dh=row["p256dh"], auth=row["auth"]),
        operator=row["operator"],
        stop_id=row["stop_id"],
        stop_name=row["stop_name"],
        line_id=row["line_id"],
        line_label=row["line_label"],
        time=row["time"],
        lead_min=row["lead_min"],
    )


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("DB_PATH", "data/vemai.db")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def add_subscription(self, sub: SubscriptionIn) -> Subscription:
        # Reativar o mesmo alerta só atualiza a antecedência, em vez de duplicar o aviso.
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                """INSERT INTO subscriptions
                   (endpoint, p256dh, auth, operator, stop_id, stop_name, line_id, line_label, time, lead_min)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT (endpoint, operator, stop_id, line_id, time)
                   DO UPDATE SET lead_min = excluded.lead_min, p256dh = excluded.p256dh, auth = excluded.auth
                   RETURNING *""",
                (sub.endpoint, sub.keys.p256dh, sub.keys.auth, sub.operator, sub.stop_id,
                 sub.stop_name, sub.line_id, sub.line_label, sub.time, sub.lead_min),
            ).fetchone()
        return _to_subscription(row)

    def get_subscription(self, sub_id: int) -> Subscription | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
        return _to_subscription(row) if row else None

    def list_subscriptions(self, endpoint: str | None = None) -> list[Subscription]:
        query, args = "SELECT * FROM subscriptions", ()
        if endpoint is not None:
            query, args = query + " WHERE endpoint = ?", (endpoint,)
        with closing(self._connect()) as conn:
            return [_to_subscription(r) for r in conn.execute(query + " ORDER BY id", args)]

    def delete_subscription(self, sub_id: int) -> bool:
        with closing(self._connect()) as conn, conn:
            return conn.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,)).rowcount > 0

    def record_notification(self, sub_id: int, vehicle: str, kind: str, day: str) -> bool:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO notifications (subscription_id, vehicle, kind, day) VALUES (?, ?, ?, ?)",
                (sub_id, vehicle, kind, day),
            )
        return cur.rowcount == 1
