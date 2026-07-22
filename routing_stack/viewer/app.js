const form = document.querySelector("#routeForm");
const promptInput = document.querySelector("#prompt");
const stackInfo = document.querySelector("#stackInfo");
const routerSelect = document.querySelector("#router");
const routeSummary = document.querySelector("#routeSummary");
const routerDecision = document.querySelector("#routerDecision");
const candidatesEl = document.querySelector("#candidates");
const transcript = document.querySelector("#transcript");
const aiMeta = document.querySelector("#aiMeta");
const newChat = document.querySelector("#newChat");
const csvFile = document.querySelector("#csvFile");
const evaluateCsv = document.querySelector("#evaluateCsv");
const trainCsv = document.querySelector("#trainCsv");
const csvStatus = document.querySelector("#csvStatus");
const csvResult = document.querySelector("#csvResult");
const submitButton = form.querySelector('button[type="submit"]');
let isRouting = false;
let conversation = [];
let csvText = "";
const MAX_CONVERSATION_MESSAGES = 10;

const fmt = (value, digits = 3) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits);
};

const displayValue = (value) => {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return fmt(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return value.join(", ") || "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
};

function formPayload() {
  return {
    router: routerSelect.value,
    prompt: promptInput.value,
    tier: document.querySelector("#tier").value,
    task_type: document.querySelector("#taskType").value,
    difficulty: document.querySelector("#difficulty").value,
    risk_level: document.querySelector("#riskLevel").value,
    evaluation_type: document.querySelector("#evaluationType").value,
    conversation: conversation.slice(-MAX_CONVERSATION_MESSAGES),
  };
}

function resizePromptInput() {
  promptInput.style.height = "auto";
  promptInput.style.height = `${Math.min(promptInput.scrollHeight, 180)}px`;
}

function setComposerBusy(busy) {
  isRouting = busy;
  submitButton.disabled = busy;
  submitButton.textContent = busy ? "전송 중" : "전송";
  promptInput.setAttribute("aria-busy", String(busy));
}

function renderConfig(config) {
  const routers = config.routers || [];
  const defaultRouter = config.default_router || routers[0] || "";
  routerSelect.innerHTML = routers
    .map((name) => `<option value="${name}" ${name === defaultRouter ? "selected" : ""}>${name}</option>`)
    .join("");

  const models = config.models || {};
  stackInfo.innerHTML = `
    <span>라우터 서버 연결됨</span>
    <b>${routers.join(", ") || "라우터 없음"}</b>
    <small>cheap=${models.cheap || "-"}<br />mid=${models.mid || "-"}<br />premium=${models.premium || "-"}</small>
  `;
}

function clearWelcome() {
  const welcome = transcript.querySelector(".welcome-card");
  if (welcome) welcome.remove();
}

function addMessage(role, content, meta = "") {
  clearWelcome();
  const message = document.createElement("article");
  message.className = `message ${role}`;
  message.innerHTML = `
    <div class="avatar">${role === "user" ? "나" : "AI"}</div>
    <div class="bubble">
      ${meta ? `<div class="message-meta">${meta}</div>` : '<div class="message-meta"></div>'}
      <div class="message-body"></div>
    </div>
  `;
  message.querySelector(".message-body").textContent = content;
  transcript.appendChild(message);
  transcript.scrollTop = transcript.scrollHeight;
  return message;
}

function updateMessage(message, content, meta = "") {
  const metaEl = message.querySelector(".message-meta");
  if (metaEl) metaEl.textContent = meta;
  message.querySelector(".message-body").textContent = content;
  transcript.scrollTop = transcript.scrollHeight;
}

function renderSummary(router, ai) {
  routeSummary.classList.remove("empty");
  routeSummary.innerHTML = `
    <span>${router.router_name}</span>
    <b>${router.selected_model_id}</b>
    <small>${router.action_type}</small>
  `;
  aiMeta.textContent = ai.skipped ? "호출 없음" : `${ai.provider} / ${ai.model_name || "모델 없음"}`;
}

function renderDecision(payload, assistantMessage) {
  const router = payload.router;
  const ai = payload.ai;
  const diagnostics = router.diagnostics || {};
  const uncertainty = diagnostics.uncertainty || null;
  const geometricSignals = diagnostics.geometric_signals || null;
  const routingContext = payload.input?.routing_context?.router_context || null;
  renderSummary(router, ai);

  routerDecision.classList.remove("empty");
  routerDecision.innerHTML = `
    <div class="decision-row"><span>라우터</span><b>${router.router_name}</b></div>
    <div class="decision-row"><span>선택 모델</span><b>${router.selected_model_id}</b></div>
    <div class="decision-row"><span>동작</span><b>${router.action_type}</b></div>
    <div class="decision-row"><span>이유</span><b>${router.selection_reason}</b></div>
    ${routingContext ? renderRoutingContext(routingContext) : ""}
    ${uncertainty ? renderUncertainty(uncertainty) : ""}
    ${geometricSignals ? renderGeometricSignals(geometricSignals) : ""}
  `;

  candidatesEl.innerHTML = (router.candidates || [])
    .map((candidate) => {
      const selected = candidate.model_id === router.selected_model_id;
      const metrics = Object.entries(candidate.metrics || {})
        .slice(0, 4)
        .map(([key, value]) => `<span>${key}: <b>${typeof value === "number" ? fmt(value) : value}</b></span>`)
        .join("");
      return `
        <article class="candidate ${selected ? "selected" : ""}">
          <div class="candidate-head">
            <b>${candidate.model_id}</b>
            <span>${candidate.reason || ""}</span>
          </div>
          <div class="candidate-stats">
            <span>점수 <b>${fmt(candidate.score)}</b></span>
            <span>비용 <b>${fmt(candidate.cost, 2)}</b></span>
            <span>가능 <b>${candidate.feasible === null ? "-" : candidate.feasible}</b></span>
          </div>
          <div class="candidate-metrics">${metrics}</div>
        </article>
      `;
    })
    .join("");

  if (ai.skipped) {
    updateMessage(assistantMessage, "라우터가 abstain을 선택해서 AI 호출을 건너뛰었습니다.", `${router.router_name} -> abstain`);
    rememberTurn(payload.input?.prompt || "", "");
    return;
  }

  if (ai.error) {
    assistantMessage.classList.add("error");
    updateMessage(assistantMessage, `AI 오류 (${ai.model_name}): ${ai.error}`, `${router.router_name} -> ${router.selected_model_id}`);
    rememberTurn(payload.input?.prompt || "", "");
    return;
  }

  updateMessage(assistantMessage, ai.output || "", `${router.router_name} -> ${router.selected_model_id}`);
  rememberTurn(payload.input?.prompt || "", ai.output || "");
}

function renderRoutingContext(context) {
  return `
    <div class="decision-row"><span>컨텍스트</span><b>${fmt(context.context_confidence)}</b></div>
    <div class="decision-row"><span>참조 감지</span><b>${displayValue(context.has_reference_expression)}</b></div>
    <div class="decision-row"><span>참조 해결</span><b>${displayValue(context.has_resolved_reference)}</b></div>
    <div class="decision-row"><span>정보 부족</span><b>${displayValue(context.missing_context)}</b></div>
    <div class="decision-row"><span>작업 토큰</span><b>${displayValue(context.context_token_estimate)}</b></div>
  `;
}

function renderUncertainty(uncertainty) {
  return `
    <div class="decision-row"><span>확신도</span><b>${fmt(uncertainty.confidence)}</b></div>
    <div class="decision-row"><span>불확실성</span><b>${uncertainty.uncertain ? "높음" : "낮음"}</b></div>
    <div class="decision-row"><span>판단 근거</span><b>${uncertainty.reason || "-"}</b></div>
  `;
}

function renderGeometricSignals(geometricSignals) {
  if (!geometricSignals.available) {
    return `<div class="decision-row"><span>기하 신호</span><b>없음</b></div>`;
  }
  const signals = geometricSignals.signals || {};
  const activeSignals = Object.entries(signals)
    .filter(([, value]) => value)
    .map(([key]) => key);
  return `
    <div class="decision-row"><span>기하 선택</span><b>${geometricSignals.selected_model_id || "-"}</b></div>
    <div class="decision-row"><span>기하 신호</span><b>${displayValue(activeSignals)}</b></div>
  `;
}

function setCsvBusy(busy) {
  evaluateCsv.disabled = busy || !csvText;
  trainCsv.disabled = busy || !csvText;
}

function setCsvStatus(message, isEmpty = false) {
  csvStatus.textContent = message;
  csvStatus.classList.toggle("empty", isEmpty);
}

async function readCsvFile(file) {
  if (!file) {
    csvText = "";
    csvResult.innerHTML = "";
    setCsvStatus("CSV 또는 TXT를 선택하세요.", true);
    setCsvBusy(false);
    return;
  }
  csvText = await file.text();
  csvResult.innerHTML = "";
  setCsvStatus(`${file.name} 선택됨`);
  setCsvBusy(false);
}

async function postCsv(path) {
  if (!csvText.trim()) {
    setCsvStatus("CSV 또는 TXT를 먼저 선택하세요.");
    return null;
  }
  setCsvBusy(true);
  const payload = {
    csv_text: csvText,
    router: routerSelect.value,
    tier: document.querySelector("#tier").value,
  };
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || data.error || "요청 실패");
    }
    return data;
  } catch (error) {
    csvResult.innerHTML = "";
    setCsvStatus(error.message);
    return null;
  } finally {
    setCsvBusy(false);
  }
}

async function evaluateSelectedCsv() {
  setCsvStatus("정답 비교 중...");
  const data = await postCsv("/api/evaluate_csv");
  if (!data) return;
  setCsvStatus(`bucket ${fmt(data.bucket_accuracy * 100, 1)}% (${data.correct_count}/${data.row_count}) / MAE ${fmt(data.mae, 2)}`);
  csvResult.innerHTML = (data.rows || [])
    .slice(0, 80)
    .map((row) => {
      const state = row.correct ? "correct" : "wrong";
      return `
        <article class="csv-row ${state}">
          <b>${row.prompt}</b>
          <span>score ${fmt(row.expected_score, 1)} -> ${fmt(row.predicted_score, 1)} / bucket ${row.expected} -> ${row.actual}</span>
          <span>${row.selection_reason || ""}</span>
        </article>
      `;
    })
    .join("");
}

async function trainSelectedCsv() {
  setCsvStatus("학습 중...");
  const data = await postCsv("/api/train_csv");
  if (!data) return;
  setCsvStatus(`학습 완료: ${data.row_count} rows -> ${data.output_path}`);
  csvResult.innerHTML = `
    <article class="csv-row correct">
      <b>learned_label 라우터 갱신됨</b>
      <span>cheap=${data.bucket_counts?.cheap || 0}, mid=${data.bucket_counts?.mid || 0}, premium=${data.bucket_counts?.premium || 0}</span>
    </article>
  `;
  await loadConfig();
  if (data.loaded_router && [...routerSelect.options].some((option) => option.value === data.loaded_router)) {
    routerSelect.value = data.loaded_router;
  }
}

async function routePrompt(event) {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt || isRouting) return;

  const payload = formPayload();
  payload.prompt = prompt;

  addMessage("user", prompt);
  const assistantMessage = addMessage("assistant", "응답을 기다리는 중...", "라우팅 중");
  promptInput.value = "";
  resizePromptInput();
  setComposerBusy(true);

  routeSummary.textContent = "라우팅 중";
  routeSummary.classList.add("empty");
  routerDecision.textContent = "라우팅 중...";
  routerDecision.classList.add("empty");
  candidatesEl.innerHTML = "";
  aiMeta.textContent = "응답 대기";

  try {
    const response = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      assistantMessage.classList.add("error");
      updateMessage(assistantMessage, data.message || data.error || "요청 실패", "오류");
      routeSummary.textContent = "요청 실패";
      routerDecision.textContent = data.message || data.error || "요청 실패";
      aiMeta.textContent = "오류";
      return;
    }

    renderDecision(data, assistantMessage);
  } catch (error) {
    assistantMessage.classList.add("error");
    updateMessage(assistantMessage, `서버 연결 실패: ${error.message}`, "오류");
    routeSummary.textContent = "연결 실패";
    routerDecision.textContent = "viewer 서버가 router 서버에 연결하지 못했습니다.";
    aiMeta.textContent = "오류";
  } finally {
    setComposerBusy(false);
    promptInput.focus();
  }
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    if (!response.ok) {
      stackInfo.textContent = data.message || data.error || "라우터 서버 연결 실패";
      return;
    }
    renderConfig(data);
  } catch (error) {
    stackInfo.textContent = `라우터 서버 연결 실패: ${error.message}`;
  }
}

function resetChat() {
  conversation = [];
  transcript.innerHTML = `
    <div class="welcome-card">
      <h3>무엇을 라우팅할까요?</h3>
      <p>프롬프트를 입력하면 라우터 선택과 AI 응답을 한 화면에서 확인할 수 있습니다.</p>
    </div>
  `;
  routeSummary.textContent = "대기 중";
  routeSummary.classList.add("empty");
  routerDecision.textContent = "아직 요청이 없습니다.";
  routerDecision.classList.add("empty");
  candidatesEl.innerHTML = "";
  aiMeta.textContent = "대기 중";
  promptInput.value = "";
  promptInput.style.height = "auto";
}

function rememberTurn(userPrompt, assistantOutput) {
  if (userPrompt) {
    conversation.push({ role: "user", content: userPrompt });
  }
  if (assistantOutput) {
    conversation.push({ role: "assistant", content: assistantOutput });
  }
  conversation = conversation.slice(-MAX_CONVERSATION_MESSAGES);
}

promptInput.addEventListener("input", () => {
  resizePromptInput();
});

promptInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  if (event.shiftKey || event.altKey || event.isComposing) return;

  event.preventDefault();
  form.requestSubmit();
});

form.addEventListener("submit", routePrompt);
newChat.addEventListener("click", resetChat);
csvFile.addEventListener("change", () => {
  readCsvFile(csvFile.files?.[0]);
});
evaluateCsv.addEventListener("click", evaluateSelectedCsv);
trainCsv.addEventListener("click", trainSelectedCsv);
setCsvBusy(false);
loadConfig();
