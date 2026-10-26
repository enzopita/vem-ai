from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from vemai.models import StopBoard, Subscription

# "CHEGANDO!" cobre 3 minutos ou menos; um veículo nessa faixa que some provavelmente passou pelo ponto.
PASSING_THRESHOLD_MIN = 3


@dataclass(frozen=True)
class Alert:
    kind: Literal["arriving", "vanished"]
    vehicle: str
    line_label: str
    eta_min: int


def is_active(sub_time: str, now: datetime, window_min: int = 30) -> bool:
    hour, minute = map(int, sub_time.split(":"))
    day_min = 24 * 60
    diff = (now.hour * 60 + now.minute - (hour * 60 + minute)) % day_min
    if diff > day_min // 2:
        diff -= day_min
    return abs(diff) <= window_min


def detect(prev: StopBoard | None, curr: StopBoard, sub: Subscription) -> list[Alert]:
    alerts = [
        Alert("arriving", p.vehicle, p.line.label, p.eta_min)
        for p in curr.predictions
        if p.line.id == sub.line_id and p.eta_min <= sub.lead_min
    ]
    if prev is not None:
        present = {p.vehicle for p in curr.predictions}
        alerts += [
            Alert("vanished", p.vehicle, p.line.label, p.eta_min)
            for p in prev.predictions
            if p.line.id == sub.line_id
            and p.eta_min > PASSING_THRESHOLD_MIN
            and p.vehicle not in present
        ]
    return alerts
