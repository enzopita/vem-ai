from vemai.models import Line
from vemai.region import search_lines

LINES = [
    Line(id="a", label="CIRCULAR 004", description="Ferry Boat / Praias"),
    Line(id="b", label="04", description="Centro / Gonzaga"),
    Line(id="c", label="40", description="Praça Barão / Gonzaga"),
    Line(id="d", label="154", description="Valongo / Ponta da Praia"),
    Line(id="e", label="CIRCULAR 140", description="Ferry Boat / Canal 1"),
    Line(id="f", label="902 Circular 21", description="Tancredo / Canal 2 / Praias"),
]


def test_number_matches_exact_first_then_prefix():
    # "4" é a linha 04 (e a CIRCULAR 004); "40" só começa com 4.
    assert [l.id for l in search_lines(LINES, "4")] == ["a", "b", "c"]


def test_leading_zeros_and_circular_prefix_are_ignored():
    assert [l.id for l in search_lines(LINES, "004")] == ["a", "b", "c"]
    assert [l.id for l in search_lines(LINES, "circular 140")] == ["e"]


def test_intermunicipal_labels_start_with_the_number():
    # A BR Mobilidade escreve "902 Circular 21": o número é o começo do rótulo.
    assert [l.id for l in search_lines(LINES, "902")] == ["f"]


def test_text_starting_with_a_number_is_still_text():
    assert search_lines([Line(id="g", label="77", description="Rua 2 de Maio / Centro")], "2 de maio")[0].id == "g"


def test_text_matches_the_route_without_accents_or_case():
    assert [l.id for l in search_lines(LINES, "ponta da praia")] == ["d"]
    assert [l.id for l in search_lines(LINES, "praca barao")] == ["c"]


def test_blank_query_finds_nothing_and_limit_applies():
    assert search_lines(LINES, "  ") == []
    assert len(search_lines(LINES, "gonzaga", limit=1)) == 1
