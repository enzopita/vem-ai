import pytest

from vemai.scraper import (
    parse_lines,
    parse_line_detail,
    parse_line_ids,
    parse_line_map,
    parse_line_stop_names,
    parse_map_center,
    parse_predictions,
    parse_stops,
    parse_vehicles,
    with_line_map,
)

CIRCULAR_007 = "2ecd397b94205c2a35f33d0970bf53d15a548a0c"


def circular_007(fixture_html):
    detail = parse_line_detail(fixture_html("linha_007.html"), CIRCULAR_007)
    return with_line_map(detail, parse_line_map(fixture_html("mapa_linha_007.html")))


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
    assert circular.description == "Praça Barão do Rio Branco / Canal 1 / Marapé / José Menino / Praias / Conselheiro Nébias"


def test_parse_line_ids_lists_each_line_once(fixture_html):
    ids = parse_line_ids(fixture_html("linhas.html"))
    assert len(ids) == 41
    assert len(set(ids)) == len(ids)
    assert ids[0] == "867d3887e0375c31b4b8ade5572d2b40df95141f"
    assert all(len(i) == 40 for i in ids)


def test_parse_line_stop_names_reads_every_stop_of_the_line(fixture_html):
    names = parse_line_stop_names(fixture_html("mapa_linha_9306.html"))
    assert len(names) == 56
    assert names[0] == "PRAÇA GAGO COUTINHO - C"
    assert "AV. REI ALBERTO I - SENAI - B" in names
    assert "TERMINAL VALONGO (PLATAFORMA D)" in names


def test_parse_line_stop_names_unescapes_quotes():
    html = "ExibePontosLinha(-23.9, -46.3, 'RUA D\\'ÁVILA, 10', PontosIcon, 0);"
    assert parse_line_stop_names(html) == ["RUA D'ÁVILA, 10"]


def test_parse_map_center_is_the_requested_stop(fixture_html):
    lat, lng = parse_map_center(fixture_html("mapa_linha_9306.html"))
    assert (round(lat, 5), round(lng, 5)) == (-23.93749, -46.3209)


def test_parse_map_center_missing():
    assert parse_map_center("<html></html>") is None


def test_parse_predictions_reads_the_driver(fixture_html):
    board = parse_predictions(fixture_html("previsao_9306.html"), "9306")
    first = board.predictions[0]
    assert (first.vehicle, first.driver) == ("4430", "FREDERICO")
    assert all(p.driver for p in board.predictions)


def test_parse_predictions_without_driver_is_blank():
    html = (
        '<table class="table_results"><tr onclick="x(\'idLinha=ab12\')">'
        '<td><span class="link_linha_vlt">184</span></td><td><strong>4430</strong></td><td>5 minutos</td></tr></table>'
    )
    assert parse_predictions(html, "1").predictions[0].driver == ""


def test_line_detail_header_and_streets(fixture_html):
    line = circular_007(fixture_html)
    assert (line.id, line.label) == (CIRCULAR_007, "CIRCULAR 007")
    assert line.description.startswith("Praça Barão do Rio Branco / Canal 1 / Marapé")
    ida, volta = line.directions
    assert (ida.direction, ida.name) == ("ida", "Praça Mauá > José Menino")
    assert (volta.direction, volta.name) == ("volta", "José Menino > Praça Mauá")
    assert ida.streets[:2] == ["PRAÇA MAUÁ", "PRAÇA DA REPÚBLICA"]
    assert len(ida.streets) == 18
    assert volta.streets[-1] == "RUA GENERAL CÂMARA"


def test_line_detail_schedules_per_day_and_direction(fixture_html):
    line = circular_007(fixture_html)
    counts = {s.day: (len(s.ida), len(s.volta)) for s in line.schedules}
    assert counts == {"uteis": (24, 24), "sabados": (23, 23), "domingos": (23, 23)}
    weekday = line.schedules[0]
    assert (weekday.ida[0].departure, weekday.ida[0].arrival) == ("04:45", "05:16")


def test_line_detail_carries_route_shape_and_stops_from_the_map(fixture_html):
    line = circular_007(fixture_html)
    ida, volta = line.directions
    assert len(ida.path) == 103 and len(volta.path) == 94
    assert ida.path[0].model_dump() == {"lat": -23.93382281588682, "lng": -46.3291514747002}
    assert len(line.stops) == 53
    assert line.stops[0].model_dump() == {"name": "PRAÇA MAUÁ", "lat": -23.933837, "lng": -46.329266}


def test_line_map_numeric_id(fixture_html):
    assert parse_line_map(fixture_html("mapa_linha_007.html")).number == 365
    assert parse_line_map("<html></html>").number is None


def test_line_detail_unknown_to_the_operator_is_none(fixture_html):
    assert parse_line_detail(fixture_html("linha_de_outra_operadora.html"), CIRCULAR_007) is None


def test_line_detail_rejects_a_page_that_is_not_a_line():
    with pytest.raises(ValueError):
        parse_line_detail("<html><body>erro</body></html>", CIRCULAR_007)


def test_parse_vehicles_reads_concatenated_objects(fixture_html):
    vehicles = parse_vehicles(fixture_html("veiculos_007.txt"))
    assert [(v.prefix, v.driver, v.direction, v.seen_at) for v in vehicles] == [
        ("4407", "ALEX", "volta", "12:10:26"),
        ("5016", "FABRICCIO", "ida", "12:10:13"),
    ]
    assert round(vehicles[0].lat, 4) == -23.9714


def test_parse_vehicles_empty_and_unknown_direction():
    assert parse_vehicles("") == []
    assert parse_vehicles('{"prefixo":"1","lat":0,"lng":0,"sentido":0,"conteudo":""},') == []


def test_parse_lines_keeps_label_and_route(fixture_html):
    html = fixture_html("linhas.html")
    lines = parse_lines(html)
    assert [l.id for l in lines] == parse_line_ids(html)
    first = lines[0]
    assert (first.label, first.description) == (
        "CIRCULAR 004",
        "Ferry Boat / Praias / Conselheiro Nébias / Praça Mauá / Terminal Valongo / Conselheiro Nébias / Epitácio Pessoa",
    )
