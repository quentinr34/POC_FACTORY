from app.config import Settings
from app.models import Subscores
from app.scoring import compute_score


def test_compute_score_weighted():
    settings = Settings()
    subscores = Subscores(clarity=100, budget=100, urgency=100, offer_fit=100)
    assert compute_score(subscores, settings) == 100


def test_compute_score_zero():
    settings = Settings()
    subscores = Subscores(clarity=0, budget=0, urgency=0, offer_fit=0)
    assert compute_score(subscores, settings) == 0


def test_compute_score_mixed():
    settings = Settings()
    subscores = Subscores(clarity=80, budget=40, urgency=60, offer_fit=20)
    # 80*.30 + 40*.25 + 60*.20 + 20*.25 = 24 + 10 + 12 + 5 = 51
    assert compute_score(subscores, settings) == 51
