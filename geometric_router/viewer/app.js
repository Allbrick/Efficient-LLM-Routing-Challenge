const form = document.querySelector("#routeForm");
const decisionEl = document.querySelector("#decision");
const candidatesEl = document.querySelector("#candidates");
const simulationEl = document.querySelector("#simulation");
const refreshSimulation = document.querySelector("#refreshSimulation");
const refreshAllocation = document.querySelector("#refreshAllocation");
const allocationTier = document.querySelector("#allocationTier");
const allocationFilter = document.querySelector("#allocationFilter");
const allocationSummary = document.querySelector("#allocationSummary");
const allocationRows = document.querySelector("#allocationRows");

let allocationPayload = null;

const fmt = (value, digits = 3) => Number(value ?? 0).toFixed(digits);

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

function probabilityBar(label, value) {
  const pct = Math.max(0, Math.min(100, Number(value || 0) * 100));
  return `
    <div class="prob-row">
      <span>${label}</span>
      <div class="prob-track"><div style="width:${pct}%"></div></div>
      <b>${fmt(value)}</b>
    </div>
  `;
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
      const selected = candidate.model_id === data.selected_model_id;
      return `
        <article class="candidate ${selected ? "selected" : ""}">
          <div class="candidate-header">
            <b>${candidate.model_id}</b>
            <span class="badge ${candidate.feasible ? "ok" : ""}">
              ${candidate.feasible ? "feasible" : "outside"}
            </span>
          </div>
          ${probabilityBar("pass_probability", candidate.pass_probability)}
          ${probabilityBar("sufficiency_probability", candidate.sufficiency_probability)}
          <div class="kv-grid">
            <div><span>cost</span><b>${fmt(candidate.cost, 2)}</b></div>
            <div><span>distance</span><b>${fmt(candidate.distance)}</b></div>
            <div><span>radius</span><b>${fmt(candidate.radius)}</b></div>
            <div><span>normalized</span><b>${fmt(candidate.normalized_distance)}</b></div>
          </div>
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
        <div class="sim-row"><span>초과 개수</span><b>${row.cost_over_limit}</b></div>
        <div class="sim-row"><span>OK</span><b>${row.ok}</b></div>
        <div class="sim-row"><span>Under</span><b>${row.under_route}</b></div>
        <div class="sim-row"><span>Over</span><b>${row.over_route}</b></div>
        <div class="sim-row"><span>Abstain miss</span><b>${row.should_abstain ?? 0}</b></div>
        <div class="selection-counts">${Object.entries(row.selection_counts).map(([k, v]) => `<span>${k}:${v}</span>`).join("")}</div>
      </article>
    `)
    .join("");
}

function renderAllocation(payload) {
  allocationPayload = payload;
  const summary = payload.summary;
  allocationSummary.innerHTML = [
    ["total", `${fmt(summary.total_cost, 2)} / ${fmt(summary.total_budget, 2)}`],
    ["quality", fmt(summary.mean_quality)],
    ["expected", fmt(summary.mean_expected_quality)],
    ["under", `${summary.under_route} / lower ${summary.under_route_lower_bound}`],
    ["over", summary.over_route],
    ["abstain miss", summary.should_abstain],
    ["gain/cost", fmt(summary.mean_quality_gain_per_cost)],
    ["under risk", fmt(summary.mean_under_route_risk)],
  ]
    .map(([label, value]) => `<div class="summary-pill"><span>${label}</span><b>${value}</b></div>`)
    .join("");
  renderAllocationRows();
}

function renderAllocationRows() {
  if (!allocationPayload) return;
  const filter = allocationFilter.value;
  const rows = allocationPayload.rows.filter((row) => filter === "all" || row.error_type === filter);
  allocationRows.innerHTML = rows
    .map((row) => `
      <tr class="${row.error_type}">
        <td>${row.prompt_id}</td>
        <td>${row.expected_min_model}</td>
        <td>${row.selected_model_id}</td>
        <td><span class="route-error">${row.error_type}</span></td>
        <td>${fmt(row.actual_quality)}</td>
        <td>${fmt(row.cost, 2)}</td>
        <td>${fmt(row.under_route_risk)}</td>
        <td>${fmt(row.quality_gain_per_cost)}</td>
      </tr>
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
  simulationEl.textContent = "simulation 로딩 중...";
  const response = await fetch("/api/simulation");
  const data = await response.json();
  renderSimulation(data);
}

async function loadAllocation() {
  allocationRows.innerHTML = `<tr><td colspan="8">allocation 로딩 중...</td></tr>`;
  const response = await fetch(`/api/allocation?tier=${encodeURIComponent(allocationTier.value)}`);
  const data = await response.json();
  renderAllocation(data);
}

form.addEventListener("submit", routePrompt);
refreshSimulation.addEventListener("click", loadSimulation);
refreshAllocation.addEventListener("click", loadAllocation);
allocationTier.addEventListener("change", loadAllocation);
allocationFilter.addEventListener("change", renderAllocationRows);

loadSimulation();
loadAllocation();
