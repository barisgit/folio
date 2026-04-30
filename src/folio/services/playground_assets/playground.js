// src/folio/playground_ui/main.ts
var API_STATE = "/api/state";
var API_TWEAKS = "/api/tweaks";
var DEBOUNCE_MS = 250;
var NUMERIC_KINDS = /* @__PURE__ */ new Set(["size_pt", "size_mm", "opacity", "letter_spacing", "stroke_width"]);
var CHOICE_KINDS = /* @__PURE__ */ new Set(["choice", "preset", "font_choice"]);
var playgroundState = null;
var selectedPageIndex = 0;
var zoomMode = "fit-width";
var isLoadingState = false;
var draftValues = {};
var pendingUpdates = /* @__PURE__ */ new Map();
var pendingTimers = /* @__PURE__ */ new Map();
var controlDiagnostics = /* @__PURE__ */ new Map();
var statusEl = requireElement("status");
var diagnosticsEl = requireElement("diagnostics");
var tweakPanelEl = requireElement("tweak-panel");
var pageSelectorEl = requireElement("page-selector");
var previewContainerEl = requireElement("preview-container");
var previewFrameEl = requireElement("preview-frame");
var prevPageButtonEl = requireElement("prev-page");
var nextPageButtonEl = requireElement("next-page");
var zoomButtonEls = Array.from(document.querySelectorAll("[data-zoom-mode]"));
function requireElement(id) {
  const element = document.getElementById(id);
  if (!element) throw new Error(`missing playground element #${id}`);
  return element;
}
function setStatus(message) {
  statusEl.textContent = message;
}
function pendingStatus(key) {
  const current = pendingUpdates.get(key);
  if (current) return current;
  const next = { timer: null, status: "idle", message: "Saved" };
  pendingUpdates.set(key, next);
  return next;
}
function setPendingStatus(key, status, message) {
  const update = pendingStatus(key);
  update.status = status;
  update.message = message;
  renderControlStatuses();
}
function diagnosticsByKey(diagnostics) {
  const byKey = /* @__PURE__ */ new Map();
  for (const diagnostic of diagnostics) {
    if (diagnostic.key) byKey.set(diagnostic.key, diagnostic.message);
  }
  return byKey;
}
function displayDiagnostics(diagnostics) {
  diagnosticsEl.innerHTML = "";
  document.querySelectorAll(".tweak-control").forEach((node) => node.classList.remove("is-invalid"));
  document.querySelectorAll(".control-diagnostic").forEach((node) => {
    node.textContent = "";
  });
  const globalDiagnostics = (diagnostics || []).filter((diagnostic) => !diagnostic.key);
  for (const diagnostic of globalDiagnostics) {
    const item = document.createElement("li");
    item.className = `diagnostic diagnostic-${diagnostic.severity || "info"}`;
    item.textContent = diagnostic.message;
    diagnosticsEl.appendChild(item);
  }
  controlDiagnostics.clear();
  for (const [key, message] of diagnosticsByKey(diagnostics || [])) {
    controlDiagnostics.set(key, message);
    const control = document.querySelector(`[data-tweak-key="${CSS.escape(key)}"]`);
    if (control) {
      control.classList.add("is-invalid");
      const detail = control.querySelector(".control-diagnostic");
      if (detail) detail.textContent = message;
    }
  }
  diagnosticsEl.hidden = globalDiagnostics.length === 0;
}
function mergeState(nextState) {
  playgroundState = nextState;
  if (selectedPageIndex >= nextState.pages.length) selectedPageIndex = 0;
  for (const tweak of nextState.tweaks) {
    if (!(tweak.key in draftValues)) {
      draftValues[tweak.key] = nextState.values[tweak.key] ?? tweak.value ?? tweak.default;
    }
  }
}
function currentPageCount() {
  return playgroundState?.pages.length || 0;
}
function selectPage(index, scrollIntoView = true) {
  const count = currentPageCount();
  if (!count) {
    selectedPageIndex = 0;
    renderPageSelector();
    return;
  }
  selectedPageIndex = Math.max(0, Math.min(index, count - 1));
  renderPageSelector();
  updateSelectedPageCard(scrollIntoView);
}
function renderPageSelector() {
  pageSelectorEl.innerHTML = "";
  const pages = playgroundState?.pages || [];
  pageSelectorEl.disabled = pages.length === 0;
  prevPageButtonEl.disabled = pages.length === 0 || selectedPageIndex <= 0;
  nextPageButtonEl.disabled = pages.length === 0 || selectedPageIndex >= pages.length - 1;
  pages.forEach((page, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `Page ${page.pageNumber}`;
    option.title = page.filename;
    pageSelectorEl.appendChild(option);
  });
  if (selectedPageIndex >= pages.length) selectedPageIndex = 0;
  pageSelectorEl.value = String(selectedPageIndex);
  pageSelectorEl.setAttribute("aria-label", pages.length ? `Selected page ${selectedPageIndex + 1} of ${pages.length}` : "No pages rendered");
}
function liveCssValue(tweak, value) {
  if (value === null || value === void 0) return "";
  if (tweak.kind === "size_pt" || tweak.kind === "letter_spacing") return `${value}pt`;
  if (tweak.kind === "size_mm") return `${value}mm`;
  return String(value);
}
function applyLiveCssVars() {
  if (!playgroundState) return;
  for (const tweak of playgroundState.tweaks) {
    if (tweak.mode === "live" && tweak.cssVar) {
      const value = draftValues[tweak.key] ?? playgroundState.values[tweak.key] ?? tweak.default;
      previewContainerEl.style.setProperty(tweak.cssVar, liveCssValue(tweak, value));
    }
  }
}
function renderPreview() {
  const pages = playgroundState?.pages || [];
  previewFrameEl.innerHTML = "";
  previewContainerEl.classList.toggle("is-empty", pages.length === 0);
  previewContainerEl.dataset.zoom = zoomMode;
  if (isLoadingState) {
    previewFrameEl.appendChild(emptyState("Loading rendered pages\u2026", "The local server is preparing the playground state."));
    return;
  }
  if (!pages.length) {
    const message = playgroundState?.diagnostics?.length ? "The document did not render. Fix the diagnostics, then reload the playground." : "No rendered pages are available for this document.";
    previewFrameEl.appendChild(emptyState("No pages rendered", message));
    return;
  }
  pages.forEach((page, index) => {
    const card = document.createElement("article");
    card.className = "page-card";
    card.dataset.pageIndex = String(index);
    card.dataset.pageId = page.pageId;
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", `Select page ${page.pageNumber}`);
    const label = document.createElement("header");
    label.className = "page-label";
    label.innerHTML = `<span>Page ${page.pageNumber}</span><small>${escapeHtml(page.filename)}</small>`;
    const sheet = document.createElement("div");
    sheet.className = "page-sheet";
    sheet.innerHTML = page.svg;
    card.append(label, sheet);
    card.addEventListener("click", () => selectPage(index, false));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectPage(index, false);
      }
    });
    previewFrameEl.appendChild(card);
  });
  applyLiveCssVars();
  updateSelectedPageCard(false);
}
function updateSelectedPageCard(scrollIntoView) {
  const cards = Array.from(previewFrameEl.querySelectorAll(".page-card"));
  cards.forEach((card, index) => {
    const selected = index === selectedPageIndex;
    card.classList.toggle("is-selected", selected);
    card.setAttribute("aria-pressed", String(selected));
    if (selected && scrollIntoView) card.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
  renderPageSelector();
}
function emptyState(title, detail) {
  const wrapper = document.createElement("div");
  wrapper.className = "empty-state";
  const heading = document.createElement("h2");
  heading.textContent = title;
  const body = document.createElement("p");
  body.textContent = detail;
  wrapper.append(heading, body);
  return wrapper;
}
function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;"
    };
    return entities[char] || char;
  });
}
function controlInputType(tweak) {
  if (tweak.kind === "color") return "color";
  if (NUMERIC_KINDS.has(tweak.kind)) return "number";
  return "text";
}
function normalizeInputValue(tweak, value) {
  if (NUMERIC_KINDS.has(tweak.kind) && value !== "") return Number(value);
  return value;
}
function buildInput(tweak) {
  if (CHOICE_KINDS.has(tweak.kind) && Array.isArray(tweak.options)) {
    const select = document.createElement("select");
    for (const optionValue of tweak.options) {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      select.appendChild(option);
    }
    return select;
  }
  const input = document.createElement("input");
  input.type = controlInputType(tweak);
  if (input.type === "number") {
    input.step = tweak.kind === "opacity" ? "0.01" : "0.1";
    if (tweak.min !== null && tweak.min !== void 0) input.min = String(tweak.min);
    if (tweak.max !== null && tweak.max !== void 0) input.max = String(tweak.max);
  }
  return input;
}
function groupedTweaks(tweaks) {
  const groups = /* @__PURE__ */ new Map();
  for (const tweak of tweaks) {
    const groupName = tweak.group || tweak.key.split(".")[0] || "Tweaks";
    const group = groups.get(groupName) || [];
    group.push(tweak);
    groups.set(groupName, group);
  }
  return groups;
}
function renderControls() {
  tweakPanelEl.innerHTML = "";
  const tweaks = playgroundState?.tweaks || [];
  if (!tweaks.length) {
    const empty = emptyState(
      "No approved tweaks",
      "This document renders successfully, but it has not declared any approved tweakable values yet. Page previews remain available for inspection."
    );
    empty.classList.add("inspector-empty");
    tweakPanelEl.appendChild(empty);
    return;
  }
  for (const [groupName, groupTweaks] of groupedTweaks(tweaks)) {
    const section = document.createElement("section");
    section.className = "tweak-group";
    section.setAttribute("aria-labelledby", `group-${safeId(groupName)}`);
    const heading = document.createElement("h3");
    heading.id = `group-${safeId(groupName)}`;
    heading.textContent = groupName;
    section.appendChild(heading);
    for (const tweak of groupTweaks) {
      section.appendChild(renderControl(tweak));
    }
    tweakPanelEl.appendChild(section);
  }
  renderControlStatuses();
}
function renderControl(tweak) {
  const wrapper = document.createElement("article");
  wrapper.className = "tweak-control";
  wrapper.dataset.tweakKey = tweak.key;
  const label = document.createElement("label");
  label.textContent = tweak.label || tweak.name || tweak.key;
  label.htmlFor = `tweak-${safeId(tweak.key)}`;
  const meta = document.createElement("div");
  meta.className = "tweak-meta";
  meta.textContent = `${tweak.key} \xB7 ${tweak.kind} \xB7 ${tweak.mode}`;
  const row = document.createElement("div");
  row.className = "tweak-row";
  const input = buildInput(tweak);
  input.id = label.htmlFor;
  input.value = String(draftValues[tweak.key] ?? playgroundState?.values[tweak.key] ?? tweak.value ?? tweak.default ?? "");
  input.setAttribute("aria-describedby", `${input.id}-status ${input.id}-diagnostic`);
  input.addEventListener("input", () => handleTweakInput(tweak, input.value));
  input.addEventListener("change", () => handleTweakInput(tweak, input.value));
  row.appendChild(input);
  if (input instanceof HTMLInputElement && input.type === "number" && tweak.min !== null && tweak.min !== void 0 && tweak.max !== null && tweak.max !== void 0) {
    const range = document.createElement("input");
    range.type = "range";
    range.min = String(tweak.min);
    range.max = String(tweak.max);
    range.step = input.step;
    range.value = input.value;
    range.setAttribute("aria-label", `${label.textContent} slider`);
    range.addEventListener("input", () => {
      input.value = range.value;
      handleTweakInput(tweak, range.value);
    });
    input.addEventListener("input", () => {
      range.value = input.value;
    });
    row.appendChild(range);
  }
  const status = document.createElement("div");
  status.id = `${input.id}-status`;
  status.className = "control-status";
  status.setAttribute("aria-live", "polite");
  const diagnostic = document.createElement("div");
  diagnostic.id = `${input.id}-diagnostic`;
  diagnostic.className = "control-diagnostic";
  wrapper.append(label, meta, row, status, diagnostic);
  return wrapper;
}
function renderControlStatuses() {
  document.querySelectorAll(".tweak-control").forEach((control) => {
    const key = control.dataset.tweakKey;
    if (!key) return;
    const status = control.querySelector(".control-status");
    const update = pendingUpdates.get(key);
    control.dataset.status = update?.status || "idle";
    if (status) status.textContent = update?.message || "Saved";
    const diagnostic = control.querySelector(".control-diagnostic");
    if (diagnostic && controlDiagnostics.has(key)) diagnostic.textContent = controlDiagnostics.get(key) || "";
    control.classList.toggle("is-invalid", controlDiagnostics.has(key));
  });
}
function safeId(value) {
  return value.replace(/[^a-z0-9_-]/gi, "-");
}
function renderZoomControls() {
  previewContainerEl.dataset.zoom = zoomMode;
  for (const button of zoomButtonEls) {
    const active = button.dataset.zoomMode === zoomMode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  }
}
function renderAll() {
  renderPageSelector();
  renderZoomControls();
  renderPreview();
  renderControls();
  displayDiagnostics(playgroundState?.diagnostics || []);
  if (isLoadingState) setStatus("Loading playground state\u2026");
  else if (playgroundState?.tweaks?.length) setStatus(`${playgroundState.tweaks.length} tweak(s) loaded.`);
  else setStatus("No tweaks declared. Page previews are still available.");
}
function schedulePatch(tweak) {
  if (pendingTimers.has(tweak.key)) clearTimeout(pendingTimers.get(tweak.key));
  const timer = setTimeout(() => patchTweak(tweak), DEBOUNCE_MS);
  pendingTimers.set(tweak.key, timer);
  const update = pendingStatus(tweak.key);
  update.timer = timer;
  setPendingStatus(tweak.key, "pending", "Waiting to save\u2026");
}
async function patchTweak(tweak) {
  pendingTimers.delete(tweak.key);
  setPendingStatus(tweak.key, "saving", tweak.mode === "live" ? "Saving\u2026" : "Saving and rerendering\u2026");
  if (tweak.mode !== "live") setStatus("Rendering updated preview\u2026");
  else setStatus("Saving tweak\u2026");
  try {
    const response = await fetch(API_TWEAKS, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: tweak.key, value: draftValues[tweak.key] })
    });
    const payload = await response.json();
    if (!response.ok) {
      const diagnostics = payload.diagnostics || [{ severity: "error", key: tweak.key, message: "Update rejected." }];
      displayDiagnostics(diagnostics);
      setPendingStatus(tweak.key, "error", "Invalid value");
      setStatus("Update rejected.");
      return;
    }
    mergeState(payload);
    controlDiagnostics.delete(tweak.key);
    setPendingStatus(tweak.key, "saved", tweak.mode === "live" ? "Saved" : "Saved and rerendered");
    renderAll();
  } catch (error) {
    displayDiagnostics([{ severity: "error", key: tweak.key, message: String(error) }]);
    setPendingStatus(tweak.key, "error", "Update failed");
    setStatus("Update failed.");
  }
}
function handleTweakInput(tweak, rawValue) {
  const value = normalizeInputValue(tweak, rawValue);
  draftValues[tweak.key] = value;
  controlDiagnostics.delete(tweak.key);
  if (tweak.mode === "live" && tweak.cssVar) {
    previewContainerEl.style.setProperty(tweak.cssVar, liveCssValue(tweak, value));
    setStatus("Preview updated. Saving\u2026");
  } else {
    setStatus("Waiting to rerender\u2026");
  }
  schedulePatch(tweak);
}
async function loadState() {
  isLoadingState = true;
  renderAll();
  try {
    const response = await fetch(API_STATE);
    const state = await response.json();
    if (!response.ok) {
      playgroundState = { specPath: "", valuesPath: "", pages: [], tweaks: [], values: {}, diagnostics: state.diagnostics || [] };
      isLoadingState = false;
      renderAll();
      setStatus("Failed to render state.");
      return;
    }
    mergeState(state);
    isLoadingState = false;
    renderAll();
  } catch (error) {
    playgroundState = { specPath: "", valuesPath: "", pages: [], tweaks: [], values: {}, diagnostics: [{ severity: "error", key: null, message: `Failed to load state: ${error}` }] };
    isLoadingState = false;
    renderAll();
    setStatus("Failed to load state.");
  }
}
pageSelectorEl.addEventListener("change", () => {
  selectPage(Number(pageSelectorEl.value || 0));
});
prevPageButtonEl.addEventListener("click", () => selectPage(selectedPageIndex - 1));
nextPageButtonEl.addEventListener("click", () => selectPage(selectedPageIndex + 1));
previewContainerEl.addEventListener("keydown", (event) => {
  if (event.key === "ArrowUp" || event.key === "PageUp") {
    event.preventDefault();
    selectPage(selectedPageIndex - 1);
  }
  if (event.key === "ArrowDown" || event.key === "PageDown") {
    event.preventDefault();
    selectPage(selectedPageIndex + 1);
  }
});
zoomButtonEls.forEach((button) => {
  button.addEventListener("click", () => {
    zoomMode = button.dataset.zoomMode || "fit-width";
    renderZoomControls();
  });
});
loadState();
