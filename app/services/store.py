import uuid
from datetime import UTC, datetime
from typing import Protocol

from app.config import Settings
from app.models import Qualification


class StoreError(Exception):
    """Raised when persistence operations fail."""


class QualificationStore(Protocol):
    def save(self, qualification: Qualification) -> Qualification: ...

    def list(self, limit: int = 50) -> list[Qualification]: ...

    def get(self, qualification_id: str) -> Qualification | None: ...


class InMemoryStore:
    """Volatile store for local development and tests."""

    def __init__(self) -> None:
        self._data: dict[str, Qualification] = {}

    def save(self, qualification: Qualification) -> Qualification:
        stored = qualification.model_copy(
            update={
                "id": qualification.id or str(uuid.uuid4()),
                "created_at": qualification.created_at or datetime.now(UTC),
            }
        )
        self._data[stored.id] = stored
        return stored

    def list(self, limit: int = 50) -> list[Qualification]:
        items = sorted(
            self._data.values(),
            key=lambda q: q.created_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return items[:limit]

    def get(self, qualification_id: str) -> Qualification | None:
        return self._data.get(qualification_id)


class FirestoreStore:
    def __init__(self, settings: Settings) -> None:
        if not settings.gcp_project_id:
            raise StoreError("GCP_PROJECT_ID manquant pour Firestore")
        from google.cloud import firestore

        self._client = firestore.Client(project=settings.gcp_project_id)
        self._collection = settings.firestore_collection

    def save(self, qualification: Qualification) -> Qualification:
        from google.api_core.exceptions import GoogleAPIError

        doc_id = qualification.id or str(uuid.uuid4())
        created_at = qualification.created_at or datetime.now(UTC)
        stored = qualification.model_copy(update={"id": doc_id, "created_at": created_at})
        payload = stored.model_dump(mode="json")
        try:
            self._client.collection(self._collection).document(doc_id).set(payload)
        except GoogleAPIError as exc:
            raise StoreError(f"Echec d'ecriture Firestore: {exc}") from exc
        return stored

    def list(self, limit: int = 50) -> list[Qualification]:
        from google.api_core.exceptions import GoogleAPIError
        from google.cloud import firestore

        try:
            docs = (
                self._client.collection(self._collection)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
            return [Qualification.model_validate(doc.to_dict()) for doc in docs]
        except GoogleAPIError as exc:
            raise StoreError(f"Echec de lecture Firestore: {exc}") from exc

    def get(self, qualification_id: str) -> Qualification | None:
        from google.api_core.exceptions import GoogleAPIError

        try:
            doc = self._client.collection(self._collection).document(qualification_id).get()
        except GoogleAPIError as exc:
            raise StoreError(f"Echec de lecture Firestore: {exc}") from exc
        if not doc.exists:
            return None
        return Qualification.model_validate(doc.to_dict())
