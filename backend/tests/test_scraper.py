from vemai.scraper import parse_predictions, parse_stops


def test_parse_stops_extracts_id_and_name(fixture_html):
    stops = parse_stops(fixture_html("busca_conselheiro.html"))
    assert stops[0].id == "9306"
    assert stops[0].name == "AV. CONSELHEIRO NÉBIAS, 107"
    assert {s.id for s in stops} >= {"9305", "9303", "4037"}
    assert all(s.name == s.name.strip() for s in stops)


def test_parse_predictions_first_row_is_arriving(fixture_html):
    board = parse_predictions(fixture_html("previsao_9306.html"), "9306")
    first = board.predictions[0]
    assert board.stop_id == "9306"
    assert (first.line.label, first.vehicle, first.eta_min) == ("184", "4430", 0)
    assert first.line.id == "0075e7c576e0a075aeafe090180fdfc2f8a31e66"


def test_parse_predictions_reads_minutes(fixture_html):
    board = parse_predictions(fixture_html("previsao_9306.html"), "9306")
    row = next(p for p in board.predictions if p.vehicle == "4904")
    assert (row.line.label, row.eta_min) == ("08", 6)


def test_parse_predictions_other_lines(fixture_html):
    board = parse_predictions(fixture_html("previsao_9306.html"), "9306")
    circular = next(l for l in board.other_lines if l.label == "CIRCULAR 007")
    assert circular.id == "2ecd397b94205c2a35f33d0970bf53d15a548a0c"
