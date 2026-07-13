let payload = null;
let activeTier = "fast";
let activePromptId = null;
let filteredPrompts = [];

const modelOrder = ["cheap", "mid", "premium"];

const els = {
  metrics: document.getElementById("metrics"),
  promptList: document.getElementById("promptList"),
  searchInput: document.getElementById("searchInput"),
  promptMeta: document.getElementById("promptMeta"),
  promptText: document.getElementById("promptText"),
  selectedModel: document.getElementById("selectedModel"),
  scoreStrip: document.getElementById("scoreStrip"),
  candidateRows: document.getElementById("candidateRows"),
  selectedOutput: document.getElementById("selectedOutput"),
};

function fmt(value, digits = 3) {
  if (typeof value !== "number") return value;
  return value.toFixed(digits);
}

function getActivePrompt() {
  return payload.prompts.find((prompt) => prompt.prompt_id === activePromptId) || payload.prompts[0];
}

function renderMetrics() {
  const summary = payload.summary;
  const tier = summary.tier_summary[activeTier];
  const counts = modelOrder
    .map((model) => `${model}: ${tier.selection_counts[model] || 0}`)
    .join(" / ");

  const cards = [
    ["프롬프트", summary.n_prompts],
    ["데이터 행", summary.n_rows],
    ["평균 선택 품질", fmt(tier.mean_selected_quality, 3)],
    ["평균 선택 비용", fmt(tier.mean_selected_cost, 3)],
    ["선택 분포", counts],
  ];

  els.metrics.innerHTML = cards
    .map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderPromptList() {
  const query = els.searchInput.value.trim().toLowerCase();
  filteredPrompts = payload.prompts.filter((item) => {
    if (!query) return true;
    return `${item.prompt_id} ${item.prompt} ${item.domain} ${item.task_type} ${item.benchmark_id}`
      .toLowerCase()
      .includes(query);
  });

  if (!filteredPrompts.some((item) => item.prompt_id === activePromptId)) {
    activePromptId = filteredPrompts[0]?.prompt_id || payload.prompts[0].prompt_id;
  }

  els.promptList.innerHTML = filteredPrompts
    .map((item) => {
      const selected = item.routing[activeTier].selected_model_id;
      const active = item.prompt_id === activePromptId ? " active" : "";
      return `
        <button class="prompt-item${active}" data-prompt-id="${item.prompt_id}">
          <strong>${item.prompt_id} · ${item.domain} · ${item.task_type}</strong>
          <span>${item.prompt}</span>
          <span>선택: ${selected}</span>
        </button>
      `;
    })
    .join("");

  document.querySelectorAll(".prompt-item").forEach((button) => {
    button.addEventListener("click", () => {
      activePromptId = button.dataset.promptId;
      render();
    });
  });
}

function renderDetail() {
  const prompt = getActivePrompt();
  const route = prompt.routing[activeTier];
  const selectedCandidate = prompt.candidates.find(
    (candidate) => candidate.model_id === route.selected_model_id
  );

  els.promptMeta.textContent = `${prompt.prompt_id} · ${prompt.domain} · ${prompt.task_type} · ${prompt.benchmark_id}`;
  els.promptText.textContent = prompt.prompt;
  els.selectedModel.textContent = route.selected_model_id;

  els.scoreStrip.innerHTML = [
    ["선택 실제 품질", fmt(route.selected_actual_quality, 3)],
    ["선택 비용", fmt(route.selected_cost, 3)],
    ["복잡도", fmt(route.prompt_complexity, 3)],
    ["선택 Utility", fmt(route.utilities[route.selected_model_id], 3)],
  ]
    .map(([label, value]) => `<div class="score-card"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");

  const rows = [...prompt.candidates].sort(
    (a, b) => modelOrder.indexOf(a.model_id) - modelOrder.indexOf(b.model_id)
  );

  els.candidateRows.innerHTML = rows
    .map((candidate) => {
      const selected = candidate.model_id === route.selected_model_id ? " selected" : "";
      return `
        <tr class="${selected}">
          <td><span class="model-pill">${candidate.model_id}</span></td>
          <td>${fmt(candidate.actual_quality, 3)}</td>
          <td>${fmt(candidate.predicted_quality, 3)}</td>
          <td>${fmt(candidate.calibrated_quality, 3)}</td>
          <td>${fmt(route.policy_quality[candidate.model_id], 3)}</td>
          <td>${fmt(candidate.cost, 3)}</td>
          <td>${fmt(route.utilities[candidate.model_id], 3)}</td>
        </tr>
      `;
    })
    .join("");

  els.selectedOutput.textContent = selectedCandidate?.model_output || "";
}

function renderTabs() {
  document.querySelectorAll(".tier-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.tier === activeTier);
  });
}

function render() {
  renderTabs();
  renderMetrics();
  renderPromptList();
  renderDetail();
}

async function init() {
  if (window.ROUTER_EVAL) {
    payload = window.ROUTER_EVAL;
  } else {
    const response = await fetch("./router_eval.json");
    payload = await response.json();
  }
  activePromptId = payload.prompts[0].prompt_id;

  document.querySelectorAll(".tier-tab").forEach((button) => {
    button.addEventListener("click", () => {
      activeTier = button.dataset.tier;
      render();
    });
  });

  els.searchInput.addEventListener("input", render);
  render();
}

init().catch((error) => {
  document.body.innerHTML = `<pre>viewer 데이터를 읽지 못했습니다.\n${error}</pre>`;
});
