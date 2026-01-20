const apiBase = "";
let currentProject = null;
let currentJob = null;

const byId = (id) => document.getElementById(id);
const tauriInvoke = window.__TAURI__?.invoke;

function setStatus(text) {
  byId("engine-status").textContent = text;
}

function setStage(message) {
  byId("job-stage").textContent = message || "Awaiting start";
  const stage = message.toLowerCase();
  const stageMap = [
    { key: "plan", match: ["plan"] },
    { key: "render", match: ["render"] },
    { key: "stitch", match: ["stitch"] },
    { key: "audio", match: ["audio", "mux"] },
    { key: "export", match: ["export"] },
  ];
  const activeKey =
    stageMap.find((entry) => entry.match.some((word) => stage.includes(word)))?.key || null;
  document.querySelectorAll("#stage-list li").forEach((item) => {
    item.classList.toggle("active", item.dataset.stage === activeKey);
  });
}

function renderOutputs(outputs) {
  const list = byId("output-list");
  list.innerHTML = "";
  if (!outputs || Object.keys(outputs).length === 0) {
    const li = document.createElement("li");
    li.textContent = "Outputs will appear after generation.";
    list.appendChild(li);
    return;
  }
  Object.entries(outputs).forEach(([variant, url]) => {
    const li = document.createElement("li");
    const link = document.createElement("a");
    link.href = url;
    link.textContent = `${variant}.mp4`;
    link.target = "_blank";
    li.appendChild(link);
    list.appendChild(li);
  });
}

async function checkHealth() {
  try {
    const response = await fetch(`${apiBase}/health`);
    const data = await response.json();
    setStatus(data.ok ? "Online" : "Offline");
  } catch (error) {
    setStatus("Offline");
  }
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
      tab.classList.add("active");
      byId(`tab-${tab.dataset.tab}`).classList.add("active");
    });
  });
}

async function loadModels() {
  const response = await fetch(`${apiBase}/models`);
  const data = await response.json();
  byId("model-mode").value = data.mode || "procedural";
  byId("comfyui-url").value = data.comfyui?.url || "";
  byId("sd-checkpoint").value = data.sd?.checkpoint || "";
  byId("animatediff-workflow").value = data.animatediff?.workflow_path || "";
  byId("tts-model").value = data.tts?.model_path || "";
  byId("tts-engine").value = data.tts?.engine || "piper";
  byId("tts-binary").value = data.tts?.binary_path || "";
  byId("music-model").value = data.music?.model_path || "";
  byId("music-track").value = data.music?.track_path || "";
}

async function saveModels() {
  const payload = {
    mode: byId("model-mode").value,
    comfyui: { url: byId("comfyui-url").value },
    sd: { checkpoint: byId("sd-checkpoint").value },
    animatediff: { workflow_path: byId("animatediff-workflow").value },
    tts: {
      model_path: byId("tts-model").value,
      engine: byId("tts-engine").value,
      binary_path: byId("tts-binary").value,
    },
    music: {
      model_path: byId("music-model").value,
      track_path: byId("music-track").value,
    },
  };
  const response = await fetch(`${apiBase}/models`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  byId("model-errors").textContent = data.errors?.join("\n") || "Saved.";
}

async function validateSpec() {
  const spec = byId("film-spec").value;
  const response = await fetch(`${apiBase}/spec/normalize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw: spec }),
  });
  if (!response.ok) {
    alert("Spec validation failed. Check formatting.");
    return;
  }
  const data = await response.json();
  byId("film-spec").value = data.spec;
}

async function createProject() {
  const specText = byId("film-spec").value;
  const payloadResponse = await fetch(`${apiBase}/spec/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw: specText }),
  });
  const payload = await payloadResponse.json();
  const response = await fetch(`${apiBase}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  currentProject = data.project_id;
  byId("project-id").textContent = data.project_id;
}

async function runPipeline() {
  if (!currentProject) {
    alert("Create a project first.");
    return;
  }
  const specText = byId("film-spec").value;
  const payloadResponse = await fetch(`${apiBase}/spec/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw: specText }),
  });
  const payload = await payloadResponse.json();
  const response = await fetch(`${apiBase}/generate/${currentProject}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  currentJob = data.job_id;
  byId("job-status").textContent = `Running ${data.job_id}`;
  setStage("Starting");
  renderOutputs(null);
  pollStatus();
}

async function pollStatus() {
  if (!currentJob) return;
  const response = await fetch(`${apiBase}/status/${currentJob}`);
  const data = await response.json();
  byId("job-status").textContent = data.message;
  setStage(data.message);
  byId("job-progress").value = data.progress;
  byId("job-logs").textContent = data.logs.join("\n") || "No logs yet.";
  renderOutputs(data.outputs);
  if (data.state !== "completed") {
    setTimeout(pollStatus, 1000);
  }
}

async function refreshDiagnostics() {
  const response = await fetch(`${apiBase}/diagnostics`);
  const data = await response.json();
  const list = byId("diagnostics-list");
  list.innerHTML = "";
  const items = [
    `FFmpeg: ${data.ffmpeg ? "available" : "missing"}`,
    `FFmpeg Path: ${data.ffmpeg_path || "n/a"}`,
    `ComfyUI URL: ${data.comfyui || "n/a"}`,
    `ComfyUI Reachable: ${data.comfyui_reachable ? "yes" : "no"}`,
    `Vault writable: ${data.vault_writable ? "yes" : "no"}`,
    `GPU: ${data.gpu || "not detected"}`,
    `Errors: ${(data.errors || []).join(", ") || "None"}`,
  ];
  items.forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    list.appendChild(li);
  });
}

async function runTest(endpoint) {
  const response = await fetch(`${apiBase}${endpoint}`, { method: "POST" });
  const data = await response.json();
  alert(data.message || "Test complete");
}

byId("reload-ui").addEventListener("click", () => window.location.reload());
byId("open-vault").addEventListener("click", async () => {
  try {
    const response = await fetch(`${apiBase}/health`);
    const data = await response.json();
    if (tauriInvoke) {
      await tauriInvoke("open_path", { path: data.vault });
    } else {
      alert(`Vault path: ${data.vault}`);
    }
  } catch (error) {
    alert("Failed to locate vault.");
  }
});
byId("validate-spec").addEventListener("click", validateSpec);
byId("create-project").addEventListener("click", createProject);
byId("run-pipeline").addEventListener("click", runPipeline);
byId("save-models").addEventListener("click", saveModels);
byId("refresh-diagnostics").addEventListener("click", refreshDiagnostics);
byId("test-image").addEventListener("click", () => runTest("/diagnostics/test_image"));
byId("test-tts").addEventListener("click", () => runTest("/diagnostics/test_tts"));
byId("test-music").addEventListener("click", () => runTest("/diagnostics/test_music"));

setupTabs();
checkHealth();
loadModels();
refreshDiagnostics();

if (window.__TAURI__?.event?.listen) {
  window.__TAURI__.event.listen("engine-restarted", () => {
    setStatus("Restarted");
    checkHealth();
  });
}
