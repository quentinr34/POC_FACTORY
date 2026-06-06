import pytest
from pydantic import ValidationError

from app.models import ClaudeAnalysis, Subscores


def test_subscores_bounds():
    Subscores(clarity=0, budget=100, urgency=50, offer_fit=25)
    with pytest.raises(ValidationError):
        Subscores(clarity=-1, budget=0, urgency=0, offer_fit=0)
    with pytest.raises(ValidationError):
        Subscores(clarity=101, budget=0, urgency=0, offer_fit=0)


def test_claude_analysis_parses():
    analysis = ClaudeAnalysis(
        summary="Besoin clair",
        subscores=Subscores(clarity=80, budget=60, urgency=40, offer_fit=70),
        questions=["q1", "q2", "q3"],
    )
    assert len(analysis.questions) == 3
