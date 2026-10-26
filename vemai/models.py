from pydantic import BaseModel, Field


class Stop(BaseModel):
    id: str
    name: str


class Line(BaseModel):
    id: str  # hash idLinha; o rótulo varia entre a tabela ("04") e a lista ("CIRCULAR 004")
    label: str


class Prediction(BaseModel):
    line: Line
    vehicle: str
    eta_min: int  # CHEGANDO! (3 min ou menos) vira 0


class StopBoard(BaseModel):
    stop_id: str
    predictions: list[Prediction]
    other_lines: list[Line]


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class SubscriptionIn(BaseModel):
    endpoint: str
    keys: PushKeys
    operator: str
    stop_id: str
    stop_name: str
    line_id: str
    line_label: str
    time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")  # HH:MM, horário aproximado
    lead_min: int = Field(default=10, ge=1, le=30)


class Subscription(SubscriptionIn):
    id: int
