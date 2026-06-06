const $ = (id) => document.getElementById(id);

const SUBSCORE_LABELS = {
  clarity: "Clarte",
  budget: "Budget",
  urgency: "Urgence",
  offer_fit: "Compat. offre",
};

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

function renderResult(q) {
  $("score").textContent = q.score;
  $("summary").textContent = q.summary;

  $("subscores").innerHTML = Object.entries(SUBSCORE_LABELS)
    .map(
      ([key, label]) =>
        `<div class="border border-slate-200 rounded-md p-2">
          <div class="text-slate-400">${label}</div>
          <div class="font-semibold">${escapeHtml(q.subscores[key])}</div>
        </div>`
    )
    .join("");

  $("questions").innerHTML = (q.questions || [])
    .map((question) => `<li>${escapeHtml(question)}</li>`)
    .join("");

  $("result").classList.remove("hidden");
}

async function loadHistory() {
  const container = $("history");
  try {
    const resp = await fetch("/qualifications?limit=20");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const items = await resp.json();
    if (!items.length) {
      container.innerHTML = `<p class="text-slate-400 py-2">Aucune qualification pour l'instant.</p>`;
      return;
    }
    container.innerHTML = items
      .map(
        (q) => `<div class="py-2 flex items-center justify-between gap-4">
          <span class="truncate text-slate-700">${escapeHtml(q.summary)}</span>
          <span class="shrink-0 font-semibold">${escapeHtml(q.score)}/100</span>
        </div>`
      )
      .join("");
  } catch (err) {
    container.innerHTML = `<p class="text-red-600 py-2">Erreur de chargement: ${escapeHtml(err.message)}</p>`;
  }
}

async function analyze() {
  const brief = $("brief").value.trim();
  const status = $("status");
  if (!brief) {
    status.textContent = "Veuillez saisir un brief.";
    return;
  }
  $("analyze-btn").disabled = true;
  status.textContent = "Analyse en cours...";
  try {
    const resp = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brief }),
    });
    if (!resp.ok) {
      const detail = await resp.json().catch(() => ({}));
      throw new Error(detail.detail || `HTTP ${resp.status}`);
    }
    const q = await resp.json();
    renderResult(q);
    status.textContent = "Termine.";
    await loadHistory();
  } catch (err) {
    status.textContent = `Erreur: ${err.message}`;
  } finally {
    $("analyze-btn").disabled = false;
  }
}

$("analyze-btn").addEventListener("click", analyze);
$("refresh-btn").addEventListener("click", loadHistory);
document.addEventListener("DOMContentLoaded", loadHistory);
