import json
import re
import ssl
from dataclasses import dataclass
from pathlib import Path

import certifi
import httpx
from bs4 import BeautifulSoup

from vemai.models import (
    DaySchedule,
    DayType,
    Direction,
    Line,
    LineDetail,
    LineDirection,
    LinePoint,
    LineStop,
    Prediction,
    Stop,
    StopBoard,
    Trip,
    Vehicle,
)

CERT_PATH = Path(__file__).resolve().parent.parent / "certs" / "globalsign-alphassl-2026q2.pem"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

_STOP_TEXT = re.compile(r"^\s*(\d+)\s*-\s*(.+?)\s*$")
_LINE_ID = re.compile(r"idLinha=([0-9a-f]+)")
_MINUTES = re.compile(r"(\d+)\s*minuto")
_NUMBER = r"(-?\d+(?:\.\d+)?)"
_MAP_CENTER = re.compile(rf"initmap\(\s*'[^']*'\s*,\s*\d+\s*,\s*{_NUMBER}\s*,\s*{_NUMBER}")
_MAP_STOP = re.compile(rf"ExibePontosLinha\(\s*{_NUMBER}\s*,\s*{_NUMBER}\s*,\s*'((?:[^'\\]|\\.)*)'")
_MAP_PATH = re.compile(r"var\s+latlng(Ida|Volta)\s*=\s*\[(.*?)\]", re.DOTALL)
_MAP_POINT = re.compile(rf"lat\s*:\s*{_NUMBER}\s*,\s*lng\s*:\s*{_NUMBER}")
_MAP_LINE_NUMBER = re.compile(r"var\s+var_linha\s*=\s*(\d+)")
_TIME = re.compile(r"^\d{2}:\d{2}$")
# Chave sem espaços: o site escreve "Domingos/Feriados" no botão e "Domingos / Feriados" no título.
_DAYS: dict[str, DayType] = {"diasúteis": "uteis", "sábados": "sabados", "domingos/feriados": "domingos"}
_DIRECTIONS: dict[str, Direction] = {"IDA": "ida", "VOLTA": "volta"}
_BUS_DIRECTIONS: dict[int, Direction] = {1: "ida", 2: "volta"}


class UpstreamError(Exception):
    pass


def parse_stops(html: str) -> list[Stop]:
    stops = []
    for a in BeautifulSoup(html, "html.parser").select("a.btn_ponto"):
        m = _STOP_TEXT.match(a.get_text())
        if m:
            stops.append(Stop(id=m.group(1), name=m.group(2)))
    return stops


def _eta_minutes(cell_text: str) -> int:
    if "CHEGANDO" in cell_text:
        return 0
    m = _MINUTES.search(cell_text)
    if not m:
        raise ValueError(f"previsão desconhecida: {cell_text!r}")
    return int(m.group(1))


def parse_predictions(html: str, stop_id: str) -> StopBoard:
    soup = BeautifulSoup(html, "html.parser")
    predictions = []
    for row in soup.select("table.table_results tr[onclick]"):
        line_id = _LINE_ID.search(row["onclick"])
        label_span = row.select_one("span.link_linha_vlt")
        cells = row.find_all("td")
        if not (line_id and label_span and len(cells) >= 3):
            continue
        label = next(label_span.stripped_strings)
        vehicle = cells[1].find("strong").get_text(strip=True)
        driver_icon = cells[1].select_one("i.fa-user-alt")
        driver = driver_icon.parent.get_text(strip=True) if driver_icon else ""
        eta = _eta_minutes(cells[2].get_text(" ", strip=True))
        predictions.append(
            Prediction(line=Line(id=line_id.group(1), label=label), vehicle=vehicle, driver=driver, eta_min=eta)
        )
    return StopBoard(stop_id=stop_id, predictions=predictions, other_lines=_select_lines(soup.select("#other_linhas a.select_lines")))


def _select_lines(anchors) -> list[Line]:
    """O site lista linhas sempre igual: rótulo em <strong> e itinerário resumido no segundo <span>."""
    lines = []
    for a in anchors:
        line_id = _LINE_ID.search(a.get("href", ""))
        label = a.find("strong")
        if line_id and label:
            spans = a.find_all("span")
            description = spans[1].get_text(" ", strip=True) if len(spans) > 1 else ""
            lines.append(Line(id=line_id.group(1), label=label.get_text(strip=True), description=description))
    return lines


def parse_lines(html: str) -> list[Line]:
    return _select_lines(BeautifulSoup(html, "html.parser").select("a.select_lines"))


def parse_line_ids(html: str) -> list[str]:
    return list(dict.fromkeys(_LINE_ID.findall(html)))


def parse_line_stop_names(html: str) -> list[str]:
    return [stop.name for stop in parse_line_map(html).stops]


def parse_map_center(html: str) -> tuple[float, float] | None:
    """Centro do mapa da linha: o site o posiciona no ponto pedido em idPonto, mesmo que a linha não o atenda."""
    m = _MAP_CENTER.search(html)
    return (float(m.group(1)), float(m.group(2))) if m else None


@dataclass(frozen=True)
class LineMap:
    paths: dict[Direction, list[LinePoint]]
    stops: list[LineStop]
    number: int | None  # id numérico interno que o rastreamento ao vivo pede no lugar do hash


def parse_line_map(html: str) -> LineMap:
    paths: dict[Direction, list[LinePoint]] = {
        _DIRECTIONS[m.group(1).upper()]: [LinePoint(lat=float(lat), lng=float(lng)) for lat, lng in _MAP_POINT.findall(m.group(2))]
        for m in _MAP_PATH.finditer(html)
    }
    stops = [
        LineStop(name=re.sub(r"\\(.)", r"\1", m.group(3)).strip(), lat=float(m.group(1)), lng=float(m.group(2)))
        for m in _MAP_STOP.finditer(html)
    ]
    number = _MAP_LINE_NUMBER.search(html)
    return LineMap(paths=paths, stops=stops, number=int(number.group(1)) if number else None)


def _trips(table) -> tuple[Direction, str, list[Trip]] | None:
    """Uma tabela de horários: o cabeçalho traz o sentido ("IDA") e o trajeto ("Praça Mauá > José Menino")."""
    header = table.find("td")
    words = list(header.stripped_strings) if header else []
    direction = _DIRECTIONS.get(words[0].upper()) if words else None
    if direction is None:
        return None
    trips = []
    for row in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) == 2 and all(_TIME.match(c) for c in cells):
            trips.append(Trip(departure=cells[0], arrival=cells[1]))
    return direction, " ".join(words[1:]), trips


def parse_line_detail(html: str, line_id: str) -> LineDetail | None:
    """Sem o traçado e os pontos, que vêm do mapa (with_line_map). None quando a operadora não conhece a linha."""
    soup = BeautifulSoup(html, "html.parser")
    header = soup.select_one("#linha_detalhes")
    if header is None:
        raise ValueError("página de linha sem #linha_detalhes")
    label = header.find("h1").get_text(strip=True) if header.find("h1") else ""
    if not label:
        return None
    description = header.find("p").get_text(strip=True) if header.find("p") else ""

    streets: dict[Direction, list[str]] = {}
    for h2 in soup.select("#div_itinerario h2"):
        direction = _DIRECTIONS.get(h2.get_text(strip=True).upper())
        listing = h2.find_next_sibling("p")
        if direction and listing:
            streets[direction] = [s.strip() for s in listing.stripped_strings if s.strip()]

    names: dict[Direction, str] = {}
    schedules = []
    for day_div in soup.select("#div_tabela > div"):
        title = day_div.find("h2")
        day = _DAYS.get("".join(title.get_text().split()).lower()) if title else None
        if day is None:
            continue
        by_direction: dict[Direction, list[Trip]] = {"ida": [], "volta": []}
        for table in day_div.find_all("table"):
            parsed = _trips(table)
            if parsed:
                direction, name, trips = parsed
                by_direction[direction] = trips
                if name:
                    names.setdefault(direction, name)
        schedules.append(DaySchedule(day=day, ida=by_direction["ida"], volta=by_direction["volta"]))

    directions = [
        LineDirection(direction=d, name=names.get(d, ""), streets=streets.get(d, []), path=[])
        for d in ("ida", "volta")
        if d in streets or d in names
    ]
    return LineDetail(id=line_id, label=label, description=description, directions=directions, stops=[], schedules=schedules)


def with_line_map(detail: LineDetail, line_map: LineMap) -> LineDetail:
    directions = [d.model_copy(update={"path": line_map.paths.get(d.direction, [])}) for d in detail.directions]
    return detail.model_copy(update={"directions": directions, "stops": line_map.stops})


def _popup_fields(html: str) -> dict[str, str]:
    """'<b>Motorista: </b>ALEX<br>' vira {'Motorista': 'ALEX'}."""
    fields = {}
    for b in BeautifulSoup(html, "html.parser").find_all("b"):
        value = b.next_sibling
        if isinstance(value, str):
            fields[b.get_text(strip=True).rstrip(":").strip()] = value.strip()
    return fields


def parse_vehicles(payload: str) -> list[Vehicle]:
    # O site concatena objetos JSON separados por vírgula, sem colchetes e com vírgula no fim.
    decoder = json.JSONDecoder()
    vehicles, pos = [], 0
    while True:
        while pos < len(payload) and payload[pos] in " \t\r\n,":
            pos += 1
        if pos >= len(payload):
            return vehicles
        raw, pos = decoder.raw_decode(payload, pos)
        direction = _BUS_DIRECTIONS.get(raw.get("sentido"))
        if direction is None:
            continue
        fields = _popup_fields(raw.get("conteudo", ""))
        vehicles.append(Vehicle(
            prefix=str(raw["prefixo"]),
            driver=fields.get("Motorista", ""),
            lat=float(raw["lat"]),
            lng=float(raw["lng"]),
            direction=direction,
            seen_at=fields.get("Horário", ""),
        ))


def build_ssl_context() -> ssl.SSLContext:
    # O servidor não envia o certificado intermediário; sem ele a verificação falha.
    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.load_verify_locations(cafile=str(CERT_PATH))
    return ctx


class OperatorClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"User-Agent": USER_AGENT},
            verify=build_ssl_context(),
            timeout=timeout,
        )
        self._line_numbers: dict[str, int] = {}

    async def _request(self, method: str, path: str, allow_server_error: bool = False, **kwargs) -> str:
        try:
            resp = await self._http.request(method, path, **kwargs)
            if not (allow_server_error and resp.status_code == 500):
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpstreamError(f"falha ao consultar a operadora: {exc}") from exc
        return resp.text

    async def _post(self, path: str, data: dict[str, str]) -> str:
        return await self._request("POST", path, data=data)

    async def search_stops(self, query: str) -> list[Stop]:
        return parse_stops(await self._post("/parts/select_option.php", {"var_pesq": query}))

    async def board(self, stop_id: str) -> StopBoard:
        html = await self._post("/parts/atualiza_previsao.php", {"idPonto": stop_id})
        return parse_predictions(html, stop_id)

    async def lines(self) -> list[Line]:
        return parse_lines(await self._request("GET", "/pg_FindLines.php"))

    async def list_lines(self) -> list[str]:
        return parse_line_ids(await self._request("GET", "/pg_FindLines.php"))

    async def line_stop_names(self, line_id: str) -> list[str]:
        return parse_line_stop_names(await self._map_page(line_id, ""))

    async def stop_location(self, stop_id: str, line_id: str) -> tuple[float, float] | None:
        return parse_map_center(await self._map_page(line_id, stop_id))

    async def line_detail(self, line_id: str) -> LineDetail | None:
        # Para uma linha de outra operadora o site responde 500 com a página cortada logo após o cabeçalho vazio.
        html = await self._request("GET", "/pg_FindLinesDt.php", allow_server_error=True, params={"idLinha": line_id})
        try:
            detail = parse_line_detail(html, line_id)
        except ValueError as exc:
            raise UpstreamError(f"resposta inesperada da operadora: {exc}") from exc
        if detail is None:
            return None
        line_map = parse_line_map(await self._map_page(line_id, ""))
        if line_map.number is not None:
            self._line_numbers[line_id] = line_map.number
        return with_line_map(detail, line_map)

    async def vehicles(self, line_id: str) -> list[Vehicle] | None:
        """Posições ao vivo; None quando a operadora não conhece a linha."""
        number = self._line_numbers.get(line_id)
        if number is None:
            number = parse_line_map(await self._map_page(line_id, "", allow_server_error=True)).number
            if number is None:
                return None
            self._line_numbers[line_id] = number
        try:
            return parse_vehicles(await self._post("/parts/update_bus.php", {"linha_id": str(number)}))
        except ValueError as exc:
            raise UpstreamError(f"resposta inesperada da operadora: {exc}") from exc

    async def _map_page(self, line_id: str, stop_id: str, allow_server_error: bool = False) -> str:
        return await self._request(
            "GET", "/pg_mapaLinha.php", allow_server_error=allow_server_error, params={"idLinha": line_id, "idPonto": stop_id}
        )

    async def aclose(self) -> None:
        await self._http.aclose()
