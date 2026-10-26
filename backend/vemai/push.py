import asyncio
import base64
import json
import os
from pathlib import Path
from urllib.parse import quote

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from vemai.models import Subscription


class SubscriptionGone(Exception):
    """O serviço de push respondeu 404/410: o navegador cancelou a inscrição."""


class PushSender:
    def __init__(self, key_path: str = "data/vapid_private.pem", subject: str | None = None):
        path = Path(key_path)
        if path.exists():
            self._vapid = Vapid.from_file(str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._vapid = Vapid()
            self._vapid.generate_keys()
            self._vapid.save_key(str(path))
        self._subject = subject or os.environ.get("VAPID_SUBJECT", "mailto:admin@example.com")

    @property
    def public_key(self) -> str:
        raw = self._vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    async def send(self, sub: Subscription, title: str, body: str) -> None:
        # O toque na notificação abre o painel do ponto do alerta, no mesmo formato de link que o front-end usa.
        url = f"/ponto/{quote(sub.stop_id, safe='')}?nome={quote(sub.stop_name, safe='')}"
        await asyncio.to_thread(self._send_blocking, sub, {"title": title, "body": body, "url": url})

    def _send_blocking(self, sub: Subscription, payload: dict) -> None:
        try:
            webpush(
                subscription_info={"endpoint": sub.endpoint, "keys": sub.keys.model_dump()},
                data=json.dumps(payload),
                vapid_private_key=self._vapid,
                vapid_claims={"sub": self._subject},
            )
        except WebPushException as exc:
            if exc.response is not None and exc.response.status_code in (404, 410):
                raise SubscriptionGone from exc
            raise
