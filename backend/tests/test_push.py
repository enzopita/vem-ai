import json

import pytest

from vemai import push
from vemai.models import Subscription

pytestmark = pytest.mark.anyio

SUB = Subscription(
    id=1,
    endpoint="https://push.example/abc",
    keys={"p256dh": "p", "auth": "a"},
    stop_id="9306",
    stop_name="AV. ANA COSTA, 130",
    line_id="l1",
    line_label="42",
    time="07:30",
)


async def test_push_opens_the_alert_stop(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(push, "webpush", lambda **kwargs: sent.append(json.loads(kwargs["data"])))
    await push.PushSender(key_path=str(tmp_path / "vapid.pem")).send(SUB, "título", "corpo")
    assert sent[0]["url"] == "/ponto/9306?nome=AV.%20ANA%20COSTA%2C%20130"
