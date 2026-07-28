const slots = ["cheap", "mid", "premium"];
let currentResults = {};
let selectedBest = null;

const el = (id) => document.getElementById(id);

function setStatus(message, isError = false) {
  const status = el("status");
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function defaultsFor(best) {
  const rank = { cheap: 0, mid: 1, premium: 2 };
  const values = {};
  for (const slot of slots) {
    if (slot === best) {
      values[`${slot}_score`] = 1.0;
      values[`${slot}_pass`] = true;
    } else if (rank[slot] > rank[best]) {
      values[`${slot}_score`] = 0.9;
      values[`${slot}_pass`] = true;
    } else {
      values[`${slot}_score`] = slot === "mid" ? 0.55 : 0.35;
      values[`${slot}_pass`] = false;
    }
  }
  return values;
}

function renderCards(results = {}) {
  const root = el("outputs");
  root.innerHTML = "";
  for (const slot of slots) {
    const result = results[slot] || {};
    const card = document.createElement("article");
    card.className = `card ${selectedBest === slot ? "selected" : ""}`;
    card.innerHTML = `
      <div class="card-header">
        <div>
          <div class="card-title">${slot}</div>
          <div class="model-name">${result.model_name || "-"}</div>
        </div>
      </div>
      <div class="card-tools">
        <label>
          Score
          <input class="score-input" id="${slot}Score" type="number" min="0" max="1" step="0.05" value="0" />
        </label>
        <label class="pass-line">
          <input id="${slot}Pass" type="checkbox" />
          pass
        </label>
        <button id="${slot}Best" type="button">Best & Save</button>
      </div>
      <div class="output">${escapeHtml(result.error ? `ERROR: ${result.error}` : result.output || "")}</div>
      <div class="card-tools">
        <button id="${slot}Select" type="button">Select Only</button>
      </div>
    `;
    root.appendChild(card);
    el(`${slot}Best`).addEventListener("click", () => chooseAndSave(slot));
    el(`${slot}Select`).addEventListener("click", () => selectBest(slot));
  }
}

function selectBest(slot) {
  selectedBest = slot;
  el("minSufficient").value = slot;
  const values = defaultsFor(slot);
  for (const item of slots) {
    el(`${item}Score`).value = values[`${item}_score`];
    el(`${item}Pass`).checked = values[`${item}_pass`];
  }
  renderSelectionState();
}

function renderSelectionState() {
  for (const card of document.querySelectorAll(".card")) {
    card.classList.remove("selected");
  }
  if (selectedBest) {
    const index = slots.indexOf(selectedBest);
    document.querySelectorAll(".card")[index]?.classList.add("selected");
  }
}

async function runAll() {
  const prompt = el("promptInput").value.trim();
  if (!prompt) {
    setStatus("Prompt를 입력하세요.", true);
    return;
  }
  selectedBest = null;
  currentResults = {};
  el("runBtn").disabled = true;
  setStatus("cheap, mid, premium 모델을 실행 중입니다...");
  renderCards({});
  try {
    const response = await fetch("/api/run_all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || payload.error || "run failed");
    currentResults = payload.results;
    renderCards(currentResults);
    setStatus("세 모델 결과가 준비됐습니다. 가장 좋은 결과의 Best & Save를 누르면 CSV에 저장됩니다.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    el("runBtn").disabled = false;
  }
}

async function chooseAndSave(slot) {
  if (!currentResults[slot]) {
    setStatus("먼저 모델을 실행하세요.", true);
    return;
  }
  selectBest(slot);
  setStatus(`${slot} 선택 결과를 저장 중입니다...`);
  const body = buildSavePayload(slot);
  try {
    const response = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || payload.error || "save failed");
    setStatus(`${payload.prompt_id} 저장 완료: ${payload.path}`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

function buildSavePayload(bestModel) {
  const outputs = {};
  for (const slot of slots) {
    outputs[slot] = currentResults[slot]?.output || "";
  }
  const payload = {
    prompt: el("promptInput").value.trim(),
    outputs,
    best_model: bestModel,
    budget_tier: el("budgetTier").value,
    task_type: el("taskType").value,
    difficulty: el("difficulty").value,
    risk_level: el("riskLevel").value,
    evaluation_type: el("evaluationType").value,
    failure_reason: el("failureReason").value,
    min_sufficient_model: el("minSufficient").value,
    abstain_is_correct: false,
  };
  for (const slot of slots) {
    payload[`${slot}_score`] = Number(el(`${slot}Score`).value || 0);
    payload[`${slot}_pass`] = el(`${slot}Pass`).checked;
  }
  return payload;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    const config = await response.json();
    el("configText").textContent = `${config.ai_provider} | cheap=${config.models.cheap}, mid=${config.models.mid}, premium=${config.models.premium} | ${config.output_path}`;
  } catch {
    el("configText").textContent = "config unavailable";
  }
}

el("runBtn").addEventListener("click", runAll);
renderCards({});
loadConfig();
