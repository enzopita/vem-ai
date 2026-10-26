from vemai.models import Line, Prediction, Stop, StopBoard
from vemai.region import merge_boards, merge_stops, tag_operator

A, B, C = Line(id="a", label="184"), Line(id="b", label="956"), Line(id="c", label="04")


def board(preds=(), other=()):
    return StopBoard(
        stop_id="9306",
        predictions=[Prediction(line=l, vehicle=v, eta_min=e) for l, v, e in preds],
        other_lines=list(other),
    )


def test_merge_stops_unions_by_id_keeps_first_name_and_sorts_by_name():
    first = [Stop(id="2", name="RUA B"), Stop(id="1", name="AV. A")]
    second = [Stop(id="2", name="OUTRO NOME"), Stop(id="3", name="PRAÇA C")]
    merged = merge_stops([first, second])
    assert [(s.id, s.name) for s in merged] == [("1", "AV. A"), ("3", "PRAÇA C"), ("2", "RUA B")]


def test_merge_stops_of_nothing_is_empty():
    assert merge_stops([]) == []
    assert merge_stops([[], []]) == []


def test_merge_boards_orders_predictions_by_eta_across_operators():
    merged = merge_boards("9306", [board([(A, "1", 9), (A, "2", 3)]), board([(B, "3", 5)])])
    assert [(p.line.label, p.eta_min) for p in merged.predictions] == [("184", 3), ("956", 5), ("184", 9)]
    assert merged.stop_id == "9306"
    assert merged.unavailable == []


def test_merge_boards_other_lines_union_without_lines_that_have_predictions():
    merged = merge_boards("9306", [board([(A, "1", 3)], other=[B, C]), board([(B, "3", 5)], other=[A, C])])
    assert [l.id for l in merged.other_lines] == ["c"]


def test_merge_boards_of_nothing_is_empty():
    merged = merge_boards("9306", [])
    assert merged.predictions == [] and merged.other_lines == []


def test_tag_operator_marks_every_line_and_survives_the_merge():
    pira = tag_operator(board([(A, "1", 3)], other=[C]), "piracicabana")
    brm = tag_operator(board([(B, "2", 5)]), "brmobilidadebs")
    merged = merge_boards("9306", [pira, brm])
    assert [(p.line.label, p.line.operator) for p in merged.predictions] == [("184", "piracicabana"), ("956", "brmobilidadebs")]
    assert [(l.label, l.operator) for l in merged.other_lines] == [("04", "piracicabana")]
