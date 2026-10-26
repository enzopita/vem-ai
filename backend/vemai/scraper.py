import re
import ssl
from pathlib import Path

import certifi
import httpx
from bs4 import BeautifulSoup

from vemai.models import Line, Prediction, Stop, StopBoard

CERT_PATH = Path(__file__).resolve().parent.parent / "certs" / "globalsign-alphassl-2026q2.pem"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

_STOP_TEXT = re.compile(r"^\s*(\d+)\s*-\s*(.+?)\s*$")
_LINE_ID = re.compile(r"idLinha=([0-9a-f]+)")
_MINUTES = re.compile(r"(\d+)\s*minuto")


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
        eta = _eta_minutes(cells[2].get_text(" ", strip=True))
        predictions.append(
            Prediction(line=Line(id=line_id.group(1), label=label), vehicle=vehicle, eta_min=eta)
        )
    other_lines = []
    for a in soup.select("#other_linhas a.select_lines"):
        line_id = _LINE_ID.search(a["href"])
        if line_id:
            other_lines.append(Line(id=line_id.group(1), label=a.find("strong").get_text(strip=True)))
    return StopBoard(stop_id=stop_id, predictions=predictions, other_lines=other_lines)


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

    async def _post(self, path: str, data: dict[str, str]) -> str:
        try:
            resp = await self._http.post(path, data=data)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpstreamError(f"falha ao consultar a operadora: {exc}") from exc
        return resp.text

    async def search_stops(self, query: str) -> list[Stop]:
        return parse_stops(await self._post("/parts/select_option.php", {"var_pesq": query}))

    async def board(self, stop_id: str) -> StopBoard:
        html = await self._post("/parts/atualiza_previsao.php", {"idPonto": stop_id})
        return parse_predictions(html, stop_id)

    async def aclose(self) -> None:
        await self._http.aclose()
