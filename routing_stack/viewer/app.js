const form = document.querySelector("#routeForm");
const stackInfo = document.querySelector("#stackInfo");
const routerSelect = document.querySelector("#router");
const routerDecision = document.querySelector("#routerDecision");
const candidatesEl = document.querySelector("#candidates");
const aiOutput = document.querySelector("#aiOutput");

const fmt = (value, digits = 3) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits);
};

function formPayload() {
  return {
    router: routerSelect.value,
    prompt: document.querySelector("#prompt").value,
    tier: document.querySelector("#tier").value,
    task_type: document.querySelector("#taskType").value,
    difficulty: document.querySelector("#difficulty").value,
    risk_level: document.querySelector("#riskLevel").value,
    evaluation_type: document.querySelector("#evaluationType").value,
  };
}

function renderConfig(config) {
  const routers = config.routers || [];
  const defaultRouter = config.default_router || routers[0] || "";
  routerSelect.innerHTML = routers
    .map((name) => `<option value="${name}" ${name === defaultRouter ? "selected" : ""}>${name}</option>`)
    .join("");
  const models = config.models || {};
  stackInfo.textContent = `viewer -> router server -> ${config.ai_provider} ai | cheap=${models.cheap}, mid=${models.mid}, premium=${models.premium}`;
}

function renderDecision(payload) {
  const router = payload.router;
  const ai = payload.ai;

  routerDecision.classList.remove("empty");
  routerDecision.innerHTML = `
    <strong>${router.selected_model_id}</strong>
    <div>라우터: ${router.router_name}</div>
    <div>동작: ${router.action_type}</div>
    <div>이유: ${router.selection_reason}</div>
    <div>모델 슬롯: ${router.model_slot || "없음"}</div>
  `;

  candidatesEl.innerHTML = (router.candidates || [])
    .map((candidate) => {
      const selected = candidate.model_id === router.selected_model_id;
      const metrics = Object.entries(candidate.metrics || {})
        .slice(0, 6)
        .map(([key, value]) => `<span>${key}: <b>${typeof value === "number" ? fmt(value) : value}</b></span>`)
        .join("");
      return `
        <article class="candidate ${selected ? "selected" : ""}">
          <div class="candidate-header">
            <b>${candidate.model_id}</b>
            <span>${candidate.reason || ""}</span>
          </div>
          <div class="kv-grid">
            <div><span>점수</span><b>${fmt(candidate.score)}</b></div>
            <div><span>비용</span><b>${fmt(candidate.cost, 2)}</b></div>
            <div><span>가능 여부</span><b>${candidate.feasible === null ? "-" : candidate.feasible}</b></div>
          </div>
          <div class="metrics">${metrics}</div>
        </article>
      `;
    })
    .join("");

  aiOutput.classList.remove("empty", "error");
  if (ai.skipped) {
    aiOutput.textContent = "라우터가 abstain을 선택해서 AI 호출을 건너뛰었습니다.";
    return;
  }
  if (ai.error) {
    aiOutput.classList.add("error");
    aiOutput.textContent = `AI 오류 (${ai.model_name}): ${ai.error}`;
    return;
  }
  aiOutput.innerHTML = `
    <div class="output-meta">${ai.provider} / ${ai.model_slot} / ${ai.model_name}</div>
    <pre>${ai.output || ""}</pre>
  `;
}

async function routePrompt(event) {
  event.preventDefault();
  routerDecision.textContent = "라우팅 중...";
  routerDecision.classList.add("empty");
  candidatesEl.innerHTML = "";
  aiOutput.textContent = "AI 응답 대기 중...";
  aiOutput.classList.add("empty");

  const response = await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formPayload()),
  });
  const data = await response.json();
  if (!response.ok) {
    routerDecision.textContent = data.message || data.error || "요청 실패";
    aiOutput.textContent = "출력이 없습니다.";
    return;
  }
  renderDecision(data);
}

async function loadConfig() {
  const response = await fetch("/api/config");
  const data = await response.json();
  if (!response.ok) {
    stackInfo.textContent = data.message || data.error || "라우터 서버 연결 실패";
    return;
  }
  renderConfig(data);
}

form.addEventListener("submit", routePrompt);
loadConfig();
