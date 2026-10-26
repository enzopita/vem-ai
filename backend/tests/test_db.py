import sqlite3
from contextlib import closing

from vemai.db import Database
from vemai.models import PushKeys, SubscriptionIn


def make_sub(**over):
    data = dict(
        endpoint="https://push.example/1", keys=PushKeys(p256dh="p", auth="a"),
        stop_id="9306", stop_name="Ponto", line_id="aaa",
        line_label="184", time="08:00", lead_min=10,
    )
    return SubscriptionIn(**{**data, **over})


def test_record_notification_is_idempotent(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    sub = db.add_subscription(make_sub())
    assert db.record_notification(sub.id, "4430", "arriving", "2026-01-01") is True
    assert db.record_notification(sub.id, "4430", "arriving", "2026-01-01") is False
    assert db.record_notification(sub.id, "4430", "arriving", "2026-01-02") is True
    assert db.record_notification(sub.id, "4430", "vanished", "2026-01-01") is True


def test_adding_same_alert_twice_updates_instead_of_duplicating(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    first = db.add_subscription(make_sub(lead_min=10))
    second = db.add_subscription(make_sub(lead_min=5))
    assert second.id == first.id
    assert [s.lead_min for s in db.list_subscriptions()] == [5]


def test_delete_removes_subscription_and_its_notifications(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    sub = db.add_subscription(make_sub())
    db.record_notification(sub.id, "4430", "arriving", "2026-01-01")
    assert db.delete_subscription(sub.id) is True
    assert db.delete_subscription(sub.id) is False
    assert db.list_subscriptions() == []


def test_old_database_gains_line_operator_and_keeps_its_alerts(tmp_path):
    path = tmp_path / "antigo.db"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.executescript(
            """CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, endpoint TEXT NOT NULL, p256dh TEXT NOT NULL, auth TEXT NOT NULL,
                stop_id TEXT NOT NULL, stop_name TEXT NOT NULL, line_id TEXT NOT NULL, line_label TEXT NOT NULL,
                time TEXT NOT NULL, lead_min INTEGER NOT NULL, UNIQUE (endpoint, stop_id, line_id, time));
               INSERT INTO subscriptions (endpoint, p256dh, auth, stop_id, stop_name, line_id, line_label, time, lead_min)
               VALUES ('e', 'p', 'a', '1', 'PONTO', 'l', '42', '07:30', 10);"""
        )
    db = Database(str(path))
    assert [s.line_operator for s in db.list_subscriptions()] == [""]
    new = db.add_subscription(SubscriptionIn(
        endpoint="e", keys={"p256dh": "p", "auth": "a"}, stop_id="1", stop_name="PONTO",
        line_id="m", line_label="100", line_operator="piracicabana", time="08:00",
    ))
    assert new.line_operator == "piracicabana"
