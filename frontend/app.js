const state = {
  templates: [],
  selected: new Set(),
};

const el = (id) => document.getElementById(id);

async function checkNucleiStatus() {
  const res = await fetch("/api/nuclei/status");
  const data = await res.json();
  const badge = el("nuclei-status");
  if (data.nuclei_installed) {
    badge.textContent = "nuclei: installed";
    badge.className = "badge ok";
  } else {
    badge.textContent = "nuclei: NOT found on PATH";
    badge.className = "badge bad";
  }
}

async function loadTemplates() {
  const params = new URLSearchParams({
    search: el("search-input").value,
    severity: el("severity-select").value,
    tag: el("tag-select").value,
    source: el("source-select").value,
  });
  const res = await fetch(`/api/templates?${params}`);
  const data = await res.json();
  state.templates = data.templates;
  renderTemplateList();
  renderTagOptions(data.tags);
}

function renderTagOptions(tags) {
  const select = el("tag-select");
  const current = select.value;
  select.innerHTML = `<option value="">all tags</option>` +
    tags.map((t) => `<option value="${t}">${t}</option>`).join("");
  select.value = current;
}

function renderTemplateList() {
  const list = el("template-list");
  if (state.templates.length === 0) {
    list.innerHTML = `<div class="muted">No templates loaded yet. Click "Sync official templates" or upload a custom one.</div>`;
    return;
  }
  list.innerHTML = state.templates.map((t) => `
    <div class="template-item ${state.selected.has(t.id) ? "selected" : ""}" data-id="${t.id}">
      <span class="sev sev-${t.severity}">${t.severity}</span>
      <strong>${escapeHtml(t.name)}</strong>
      <div class="muted">${t.id} &middot; ${t.source} ${t.tags.length ? "&middot; " + t.tags.slice(0, 4).join(", ") : ""}</div>
    </div>
  `).join("");

  list.querySelectorAll(".template-item").forEach((node) => {
    node.addEventListener("click", () => {
      const id = node.dataset.id;
      if (state.selected.has(id)) state.selected.delete(id);
      else state.selected.add(id);
      node.classList.toggle("selected");
      updateSelectedCount();
    });
  });
}

function updateSelectedCount() {
  el("selected-count").textContent = `${state.selected.size} templates selected`;
  el("run-btn").disabled = state.selected.size === 0 || !el("target-input").value.trim();
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str ?? "";
  return d.innerHTML;
}

function logLine(text, cls = "") {
  const c = el("console");
  const div = document.createElement("div");
  if (cls) div.className = cls;
  div.textContent = text;
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;
}

function renderFinding(data) {
  const wrap = el("findings");
  const card = document.createElement("div");
  card.className = "finding-card";
  const info = data.info || {};
  card.innerHTML = `
    <span class="sev sev-${(info.severity || "unknown").toLowerCase()}">${info.severity || "?"}</span>
    <strong>${escapeHtml(info.name || data["template-id"] || "finding")}</strong>
    <div class="muted">${escapeHtml(data["matched-at"] || data.host || "")}</div>
  `;
  wrap.prepend(card);
}

function runScan() {
  const target = el("target-input").value.trim();
  if (!target || state.selected.size === 0) return;

  el("console").innerHTML = "";
  el("findings").innerHTML = "";
  el("run-btn").disabled = true;
  el("run-btn").textContent = "Scanning...";

  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/scan`);

  ws.onopen = () => {
    ws.send(JSON.stringify({ target, template_ids: Array.from(state.selected) }));
  };

  ws.onmessage = (msg) => {
    const evt = JSON.parse(msg.data);
    switch (evt.event) {
      case "started":
        logLine(`$ ${evt.command}`);
        break;
      case "finding":
        logLine(`[finding] ${evt.data["template-id"] || ""} -> ${evt.data["matched-at"] || evt.data.host || ""}`);
        renderFinding(evt.data);
        break;
      case "log":
        logLine(evt.message);
        break;
      case "error":
        logLine(`[error] ${evt.message}`, "muted");
        break;
      case "finished":
        logLine(`--- scan finished (exit code ${evt.returncode}) ---`);
        break;
    }
  };

  ws.onerror = () => logLine("[error] websocket connection failed");
  ws.onclose = () => {
    el("run-btn").disabled = false;
    el("run-btn").textContent = "Run Scan";
  };
}

async function syncTemplates() {
  el("sync-status").textContent = "Syncing official templates from GitHub (first run can take a minute)...";
  el("sync-btn").disabled = true;
  try {
    const res = await fetch("/api/templates/sync", { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      el("sync-status").textContent = `Loaded ${data.templates_loaded} templates.`;
      await loadTemplates();
    } else {
      el("sync-status").textContent = `Sync failed: ${data.error}`;
    }
  } finally {
    el("sync-btn").disabled = false;
  }
}

async function uploadTemplate(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/templates/upload", { method: "POST", body: form });
  const data = await res.json();
  if (data.ok) {
    el("sync-status").textContent = `Uploaded template: ${data.template.id}`;
    await loadTemplates();
  } else {
    el("sync-status").textContent = `Upload failed: ${data.error}`;
  }
}

// wire up events
el("target-input").addEventListener("input", updateSelectedCount);
el("run-btn").addEventListener("click", runScan);
el("sync-btn").addEventListener("click", syncTemplates);
el("upload-input").addEventListener("change", (e) => {
  if (e.target.files.length) uploadTemplate(e.target.files[0]);
});
[el("search-input"), el("severity-select"), el("tag-select"), el("source-select")].forEach((node) => {
  node.addEventListener("input", loadTemplates);
  node.addEventListener("change", loadTemplates);
});

checkNucleiStatus();
loadTemplates();
