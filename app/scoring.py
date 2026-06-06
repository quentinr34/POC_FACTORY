from app.config import Settings
from app.models import Subscores


def compute_score(subscores: Subscores, settings: Settings) -> int:
    weighted = (
        subscores.clarity * settings.score_weights_clarity
        + subscores.budget * settings.score_weights_budget
        + subscores.urgency * settings.score_weights_urgency
        + subscores.offer_fit * settings.score_weights_offer_fit
    )
    return max(0, min(100, round(weighted)))
