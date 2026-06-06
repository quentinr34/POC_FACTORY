import json
import re
from typing import Protocol

from pydantic import ValidationError

from app.config import Settings
from app.models import ClaudeAnalysis, Subscores

SYSTEM_PROMPT = (
    "Tu es un assistant de qualification avant-vente pour une ESN. "
    "On te fournit un brief client brut. Analyse-le et reponds UNIQUEMENT "
    "avec un objet JSON valide, sans texte autour, au format exact suivant :\n"
    '{\n'
    '  "summary": "resume structure du besoin en quelques phrases",\n'
    '  "subscores": {\n'
    '    "clarity": <entier 0-100>,\n'
    '    "budget": <entier 0-100>,\n'
    '    "urgency": <entier 0-100>,\n'
    '    "offer_fit": <entier 0-100>\n'
    '  },\n'
    '  "questions": ["question 1", "question 2", "question 3"]\n'
    "}\n"
    "Les sous-scores evaluent : clarity (clarte du besoin), budget (visibilite "
    "budgetaire), urgency (urgence/echeance), offer_fit (compatibilite avec une "
    "offre de conseil/integration). Fournis exactement 3 questions de clarification."
)


class AnalyzerError(Exception):
    """Raised when the brief analysis fails (API or parsing error)."""


class BriefAnalyzer(Protocol):
    def analyze(self, brief: str) -> ClaudeAnalysis: ...

    @property
    def model(self) -> str: ...


def parse_analysis(raw_text: str) -> ClaudeAnalysis:
    text = raw_text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AnalyzerError(f"Reponse Claude non parsable en JSON: {exc}") from exc
    try:
        return ClaudeAnalysis.model_validate(data)
    except ValidationError as exc:
        raise AnalyzerError(f"Reponse Claude invalide: {exc}") from exc


class StubBriefAnalyzer:
    """Deterministic analyzer for local demo and e2e tests (no API call)."""

    model = "stub-analyzer"

    def analyze(self, brief: str) -> ClaudeAnalysis:
        return ClaudeAnalysis(
            summary=f"Resume simule du brief ({len(brief)} caracteres).",
            subscores=Subscores(clarity=70, budget=50, urgency=60, offer_fit=80),
            questions=[
                "Quel est le budget alloue au projet ?",
                "Quelle est l'echeance souhaitee ?",
                "Quels systemes existants doivent etre integres ?",
            ],
        )


class ClaudeBriefAnalyzer:
    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            raise AnalyzerError("ANTHROPIC_API_KEY manquante")
        from anthropic import Anthropic

        self._client = Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        self._model = settings.claude_model

    @property
    def model(self) -> str:
        return self._model

    def analyze(self, brief: str) -> ClaudeAnalysis:
        from anthropic import APIError

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": brief}],
            )
        except APIError as exc:
            raise AnalyzerError(f"Echec de l'appel Claude: {exc}") from exc

        parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        if not parts:
            raise AnalyzerError("Reponse Claude vide")
        return parse_analysis("".join(parts))
