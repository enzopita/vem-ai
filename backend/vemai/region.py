import re
import unicodedata
from collections.abc import Iterable

from vemai.models import CatalogStop, Line, RegionBoard, Stop, StopBoard


def merge_stops(results: Iterable[list[Stop]]) -> list[Stop]:
    """Une os pontos das operadoras pelo id (compartilhado na região), mantendo o primeiro nome."""
    by_id: dict[str, Stop] = {}
    for stops in results:
        for stop in stops:
            by_id.setdefault(stop.id, stop)
    return sorted(by_id.values(), key=lambda s: s.name)


def merge_catalogs(results: Iterable[list[CatalogStop]]) -> list[CatalogStop]:
    by_id: dict[str, CatalogStop] = {}
    for stops in results:
        for stop in stops:
            by_id.setdefault(stop.id, stop)
    return sorted(by_id.values(), key=lambda s: s.id)


def tag_operator(board: StopBoard, operator: str) -> StopBoard:
    """Marca em cada linha a operadora que a atende: municipal e intermunicipal se distinguem por ela."""
    tag = lambda line: line.model_copy(update={"operator": operator})
    return board.model_copy(update={
        "predictions": [p.model_copy(update={"line": tag(p.line)}) for p in board.predictions],
        "other_lines": [tag(line) for line in board.other_lines],
    })


def merge_boards(stop_id: str, boards: Iterable[StopBoard]) -> RegionBoard:
    boards = list(boards)
    predictions = sorted((p for b in boards for p in b.predictions), key=lambda p: p.eta_min)
    with_prediction = {p.line.id for p in predictions}
    other: dict[str, Line] = {}
    for board in boards:
        for line in board.other_lines:
            if line.id not in with_prediction:
                other.setdefault(line.id, line)
    return RegionBoard(stop_id=stop_id, predictions=predictions, other_lines=list(other.values()))


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold().strip()


_NUMBER = re.compile(r"(?:circular\s+)?0*(\d+)")


def _line_number(label: str) -> str | None:
    """"04", "004" e "CIRCULAR 004" são a mesma linha 4; "902 Circular 21" é a 902 (cada operadora escreve de um jeito)."""
    number = _NUMBER.match(_fold(label))
    return number.group(1) if number else None


def _query_number(query: str) -> str | None:
    """A busca só é por número quando é só o número: "2 de maio" continua sendo texto."""
    number = _NUMBER.fullmatch(_fold(query))
    return number.group(1) if number else None


def search_lines(lines: list[Line], query: str, limit: int = 10) -> list[Line]:
    """Número exato primeiro, depois número que começa com o digitado; texto só quando a busca tem letras."""
    wanted = _query_number(query)
    words = _fold(query)
    ranked: list[tuple[int, Line]] = []
    for line in lines:
        number = _line_number(line.label)
        if wanted is not None and number is not None:
            if number == wanted:
                ranked.append((0, line))
            elif number.startswith(wanted):
                ranked.append((1, line))
        elif wanted is None and words and words in _fold(f"{line.label} {line.description}"):
            ranked.append((2, line))
    ranked.sort(key=lambda item: item[0])
    return [line for _, line in ranked[:limit]]
