import pytest

from app.services.analyzer import AnalyzerError, parse_analysis


def test_parse_plain_json():
    raw = (
        '{"summary": "Besoin clair", '
        '"subscores": {"clarity": 80, "budget": 60, "urgency": 40, "offer_fit": 70}, '
        '"questions": ["q1", "q2", "q3"]}'
    )
    analysis = parse_analysis(raw)
    assert analysis.summary == "Besoin clair"
    assert analysis.subscores.clarity == 80
    assert len(analysis.questions) == 3


def test_parse_fenced_json():
    raw = (
        "Voici le resultat:\n```json\n"
        '{"summary": "x", "subscores": {"clarity": 1, "budget": 2, '
        '"urgency": 3, "offer_fit": 4}, "questions": ["a", "b", "c"]}\n```'
    )
    analysis = parse_analysis(raw)
    assert analysis.subscores.offer_fit == 4


def test_parse_invalid_json_raises():
    with pytest.raises(AnalyzerError):
        parse_analysis("pas du json du tout")


def test_parse_out_of_bounds_raises():
    raw = (
        '{"summary": "x", "subscores": {"clarity": 150, "budget": 2, '
        '"urgency": 3, "offer_fit": 4}, "questions": ["a", "b", "c"]}'
    )
    with pytest.raises(AnalyzerError):
        parse_analysis(raw)
