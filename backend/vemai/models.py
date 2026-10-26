from typing import Literal

from pydantic import BaseModel, Field

Direction = Literal["ida", "volta"]
DayType = Literal["uteis", "sabados", "domingos"]


class Stop(BaseModel):
    id: str
    name: str


class Line(BaseModel):
    id: str  # hash idLinha; o rótulo varia entre a tabela ("04") e a lista ("CIRCULAR 004")
    label: str
    operator: str = ""  # operadora que atende a linha; a central preenche, o coletor não sabe quem é
    description: str = ""  # itinerário resumido; o quadro só traz para as linhas a mais de 20 min


class Prediction(BaseModel):
    line: Line
    vehicle: str
    driver: str = ""  # primeiro nome do motorista, quando o site o mostra
    eta_min: int  # CHEGANDO! (3 min ou menos) vira 0


class StopBoard(BaseModel):
    stop_id: str
    predictions: list[Prediction]
    other_lines: list[Line]


class RegionBoard(StopBoard):
    unavailable: list[str] = []  # operadoras cujo coletor falhou nesta leitura


class StopSearch(BaseModel):
    stops: list[Stop]
    unavailable: list[str] = []


class CatalogStop(BaseModel):
    id: str
    name: str
    lat: float
    lng: float


class LineSearch(BaseModel):
    lines: list[Line]
    unavailable: list[str] = []


class StopCatalog(BaseModel):
    stops: list[CatalogStop]
    unavailable: list[str] = []


class LinePoint(BaseModel):
    lat: float
    lng: float


class LineStop(BaseModel):
    name: str  # o mapa da linha não dá o código do ponto
    lat: float
    lng: float


class Trip(BaseModel):
    departure: str  # HH:MM
    arrival: str


class LineDirection(BaseModel):
    direction: Direction
    name: str  # "Praça Mauá > José Menino"
    streets: list[str]
    path: list[LinePoint]


class DaySchedule(BaseModel):
    day: DayType
    ida: list[Trip]
    volta: list[Trip]


class LineDetail(BaseModel):
    id: str
    label: str
    description: str
    operator: str = ""
    directions: list[LineDirection]
    stops: list[LineStop]
    schedules: list[DaySchedule]


class Vehicle(BaseModel):
    prefix: str
    driver: str
    lat: float
    lng: float
    direction: Direction
    seen_at: str  # HH:MM:SS da última posição, no relógio da operadora


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class SubscriptionIn(BaseModel):
    endpoint: str
    keys: PushKeys
    stop_id: str
    stop_name: str
    line_id: str
    line_label: str
    line_operator: str = ""  # vazio em alertas criados antes da cor por tipo de linha
    time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")  # HH:MM, horário aproximado
    lead_min: int = Field(default=10, ge=1, le=30)


class Subscription(SubscriptionIn):
    id: int
