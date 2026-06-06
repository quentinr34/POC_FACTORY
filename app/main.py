from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import __version__
from app.config import Settings, get_settings
from app.models import BriefRequest, Qualification
from app.scoring import compute_score
from app.services.analyzer import AnalyzerError, BriefAnalyzer, ClaudeBriefAnalyzer

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Quote Catcher", version=__version__)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def get_analyzer(settings: Annotated[Settings, Depends(get_settings)]) -> BriefAnalyzer:
    try:
        return ClaudeBriefAnalyzer(settings)
    except AnalyzerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/analyze", response_model=Qualification)
def analyze(
    payload: BriefRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    analyzer: Annotated[BriefAnalyzer, Depends(get_analyzer)],
) -> Qualification:
    try:
        analysis = analyzer.analyze(payload.brief)
    except AnalyzerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    score = compute_score(analysis.subscores, settings)
    return Qualification(
        brief_raw=payload.brief,
        summary=analysis.summary,
        subscores=analysis.subscores,
        score=score,
        questions=analysis.questions,
        model=analyzer.model,
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    settings = get_settings()
    return templates.TemplateResponse(
        request, "index.html", {"app_name": settings.app_name}
    )
