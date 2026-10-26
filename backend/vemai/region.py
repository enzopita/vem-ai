from collections.abc import Iterable

from vemai.models import Line, RegionBoard, Stop, StopBoard


def merge_stops(results: Iterable[list[Stop]]) -> list[Stop]:
    """Une os pontos das operadoras pelo id (compartilhado na região), mantendo o primeiro nome."""
    by_id: dict[str, Stop] = {}
    for stops in results:
        for stop in stops:
            by_id.setdefault(stop.id, stop)
    return sorted(by_id.values(), key=lambda s: s.name)


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
