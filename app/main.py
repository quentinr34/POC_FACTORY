import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.config import Settings, get_settings
from app.logging_config import configure_logging
from app.models import BriefRequest, Qualification
from app.scoring import compute_score
from app.services.analyzer import (
    AnalyzerError,
    BriefAnalyzer,
    ClaudeBriefAnalyzer,
    StubBriefAnalyzer,
)
from app.services.store import FirestoreStore, InMemoryStore, QualificationStore, StoreError

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

configure_logging()
logger = logging.getLogger("quote_catcher")

app = FastAPI(title="Quote Catcher", version=__version__)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


app.add_middleware(AccessLogMiddleware)


@lru_cache
def _memory_store() -> InMemoryStore:
    return InMemoryStore()


def get_analyzer(settings: Annotated[Settings, Depends(get_settings)]) -> BriefAnalyzer:
    if settings.use_stub_analyzer:
        return StubBriefAnalyzer()
    try:
        return ClaudeBriefAnalyzer(settings)
    except AnalyzerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_store(settings: Annotated[Settings, Depends(get_settings)]) -> QualificationStore:
    if settings.gcp_project_id:
        try:
            return FirestoreStore(settings)
        except StoreError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _memory_store()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/analyze", response_model=Qualification)
def analyze(
    payload: BriefRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    analyzer: Annotated[BriefAnalyzer, Depends(get_analyzer)],
    store: Annotated[QualificationStore, Depends(get_store)],
) -> Qualification:
    try:
        analysis = analyzer.analyze(payload.brief)
    except AnalyzerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    score = compute_score(analysis.subscores, settings)
    qualification = Qualification(
        brief_raw=payload.brief,
        summary=analysis.summary,
        subscores=analysis.subscores,
        score=score,
        questions=analysis.questions,
        model=analyzer.model,
    )
    try:
        return store.save(qualification)
    except StoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/qualifications", response_model=list[Qualification])
def list_qualifications(
    store: Annotated[QualificationStore, Depends(get_store)],
    limit: int = 50,
) -> list[Qualification]:
    try:
        return store.list(limit=limit)
    except StoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/qualifications/{qualification_id}", response_model=Qualification)
def get_qualification(
    qualification_id: str,
    store: Annotated[QualificationStore, Depends(get_store)],
) -> Qualification:
    try:
        result = store.get(qualification_id)
    except StoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Qualification introuvable")
    return result


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    settings = get_settings()
    return templates.TemplateResponse(
        request, "index.html", {"app_name": settings.app_name}
    )
