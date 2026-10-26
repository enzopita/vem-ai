from pydantic import BaseModel


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
