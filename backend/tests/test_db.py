from vemai.db import Database
from vemai.models import PushKeys, SubscriptionIn


def make_sub(**over):
    data = dict(
        endpoint="https://push.example/1", keys=PushKeys(p256dh="p", auth="a"),
        operator="piracicabana", stop_id="9306", stop_name="Ponto", line_id="aaa",
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
