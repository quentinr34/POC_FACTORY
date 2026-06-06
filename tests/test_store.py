from app.models import Qualification, Subscores
from app.services.store import InMemoryStore


def _make(summary: str) -> Qualification:
    return Qualification(
        brief_raw="brief",
        summary=summary,
        subscores=Subscores(clarity=50, budget=50, urgency=50, offer_fit=50),
        score=50,
        questions=["a", "b", "c"],
        model="test",
    )


def test_save_assigns_id_and_created_at():
    store = InMemoryStore()
    saved = store.save(_make("un"))
    assert saved.id is not None
    assert saved.created_at is not None


def test_get_returns_saved():
    store = InMemoryStore()
    saved = store.save(_make("un"))
    fetched = store.get(saved.id)
    assert fetched is not None
    assert fetched.summary == "un"


def test_get_missing_returns_none():
    store = InMemoryStore()
    assert store.get("inconnu") is None


def test_list_orders_recent_first_and_limits():
    store = InMemoryStore()
    store.save(_make("un"))
    store.save(_make("deux"))
    store.save(_make("trois"))
    items = store.list(limit=2)
    assert len(items) == 2
