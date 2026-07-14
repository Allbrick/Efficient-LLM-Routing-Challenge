const form = document.querySelector("#routeForm");
const decisionEl = document.querySelector("#decision");
const candidatesEl = document.querySelector("#candidates");
const simulationEl = document.querySelector("#simulation");
const refreshSimulation = document.querySelector("#refreshSimulation");

const fmt = (value, digits = 3) => Number(value).toFixed(digits);

function formPayload() {
  return {
    prompt: document.querySelector("#prompt").value,
    tier: document.querySelector("#tier").value,
    task_type: document.querySelector("#taskType").value,
    difficulty: document.querySelector("#difficulty").value,
    risk_level: document.querySelector("#riskLevel").value,
    evaluation_type: document.querySelector("#evaluationType").value,
  };
}

function renderDecision(data) {
  const evidence = Object.entries(data.evidence)
    .map(([key, value]) => `
      <div class="metric">
        <span>${key}</span>
        <b>${fmt(value)}</b>
      </div>
    `)
    .join("");

  const frontier = data.frontier_hint
    ? `${data.frontier_hint.model_id} · cost ${fmt(data.frontier_hint.cost, 2)} · quality ${fmt(data.frontier_hint.quality)}`
    : "없음";

  decisionEl.classList.remove("empty");
  decisionEl.innerHTML = `
    <strong>${data.selected_model_id}</strong>
    <div>tier: ${data.budget_tier}</div>
    <div>reason: ${data.selection_reason}</div>
    <div>frontier hint: ${frontier}</div>
    <div class="evidence">${evidence}</div>
  `;

  candidatesEl.innerHTML = data.candidates
    .map((candidate) => {
      const ratio = Math.min(candidate.normalized_distance, 1.5);
      const width = Math.max(4, Math.min(100, (ratio / 1.5) * 100));
      return `
        <article class="candidate">
          <div class="candidate-header">
            <b>${candidate.model_id}</b>
            <span class="badge ${candidate.feasible ? "ok" : ""}">
              ${candidate.feasible ? "feasible" : "outside"}
            </span>
          </div>
          <div class="bar"><div style="width:${width}%"></div></div>
          <div class="sim-row"><span>distance</span><b>${fmt(candidate.distance)}</b></div>
          <div class="sim-row"><span>radius</span><b>${fmt(candidate.radius)}</b></div>
          <div class="sim-row"><span>normalized</span><b>${fmt(candidate.normalized_distance)}</b></div>
          <div class="sim-row"><span>pass 확률</span><b>${fmt(candidate.pass_probability)}</b></div>
          <div class="sim-row"><span>충분 확률</span><b>${fmt(candidate.sufficiency_probability)}</b></div>
          <div class="sim-row"><span>cost</span><b>${fmt(candidate.cost, 2)}</b></div>
        </article>
      `;
    })
    .join("");
}

function renderSimulation(payload) {
  const summary = payload.summary.tier_summary;
  simulationEl.innerHTML = Object.entries(summary)
    .map(([tier, row]) => `
      <article class="sim-card">
        <h3>${tier}</h3>
        <div class="sim-row"><span>Budget limit</span><b>${fmt(row.budget_limit, 3)}</b></div>
        <div class="sim-row"><span>평균 품질</span><b>${fmt(row.mean_quality)}</b></div>
        <div class="sim-row"><span>평균 비용</span><b>${fmt(row.mean_cost, 3)}</b></div>
        <div class="sim-row"><span>초과 횟수</span><b>${row.cost_over_limit}</b></div>
        <div class="sim-row"><span>평균 초과 비용</span><b>${fmt(row.mean_excess_cost, 3)}</b></div>
        <div class="sim-row"><span>OK</span><b>${row.ok}</b></div>
        <div class="sim-row"><span>Under-route</span><b>${row.under_route}</b></div>
        <div class="sim-row"><span>Over-route</span><b>${row.over_route}</b></div>
        <div class="sim-row"><span>선택 분포</span><b>${Object.entries(row.selection_counts).map(([k, v]) => `${k}:${v}`).join(" ")}</b></div>
      </article>
    `)
    .join("");
}

async function routePrompt(event) {
  event.preventDefault();
  decisionEl.textContent = "라우팅 중...";
  decisionEl.classList.add("empty");
  candidatesEl.innerHTML = "";

  const response = await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formPayload()),
  });
  const data = await response.json();
  if (!response.ok) {
    decisionEl.textContent = data.message || data.error || "라우팅 실패";
    return;
  }
  renderDecision(data);
}

async function loadSimulation() {
  simulationEl.textContent = "시뮬레이션 로딩 중...";
  const response = await fetch("/api/simulation");
  const data = await response.json();
  renderSimulation(data);
}

form.addEventListener("submit", routePrompt);
refreshSimulation.addEventListener("click", loadSimulation);
loadSimulation();
