from datetime import datetime

from vemai.alerts import Alert, detect, is_active
from vemai.models import Line, Prediction, PushKeys, StopBoard, Subscription

LINE = Line(id="aaa", label="184")
OTHER = Line(id="bbb", label="08")


def sub(lead_min=10):
    return Subscription(
        id=1, endpoint="https://push.example/1", keys=PushKeys(p256dh="p", auth="a"),
        stop_id="9306", stop_name="Ponto", line_id="aaa",
        line_label="184", time="08:00", lead_min=lead_min,
    )


def board(*preds):
    return StopBoard(
        stop_id="9306",
        predictions=[Prediction(line=l, vehicle=v, eta_min=e) for l, v, e in preds],
        other_lines=[],
    )


def test_arriving_within_lead_but_not_beyond():
    curr = board((LINE, "1", 10), (LINE, "2", 11), (OTHER, "3", 2))
    assert detect(None, curr, sub(lead_min=10)) == [Alert("arriving", "1", "184", 10)]


def test_vanished_when_previous_eta_above_three():
    prev = board((LINE, "1", 8))
    curr = board((LINE, "2", 25))
    assert detect(prev, curr, sub()) == [Alert("vanished", "1", "184", 8)]


def test_not_vanished_when_it_probably_passed_the_stop():
    prev = board((LINE, "1", 3), (LINE, "2", 0))
    assert detect(prev, board(), sub()) == []


def test_no_vanished_without_previous_board():
    assert detect(None, board(), sub()) == []


def test_vanished_ignores_other_lines_and_still_present_vehicles():
    prev = board((LINE, "1", 8), (OTHER, "9", 8))
    curr = board((LINE, "1", 7))
    assert detect(prev, curr, sub(lead_min=5)) == []


def test_is_active_window():
    at = lambda h, m: datetime(2026, 1, 1, h, m)
    assert is_active("08:00", at(7, 30))
    assert is_active("08:00", at(8, 30))
    assert not is_active("08:00", at(7, 29))
    assert not is_active("08:00", at(8, 31))


def test_is_active_crossing_midnight():
    at = lambda h, m: datetime(2026, 1, 1, h, m)
    assert is_active("23:50", at(0, 10))
    assert is_active("00:10", at(23, 45))
    assert not is_active("23:50", at(0, 25))
