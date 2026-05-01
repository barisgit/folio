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
var pageObserver = null;
var savedPulseTimer = null;
var suppressObserverUntil = 0;
var statusEl = requireElement("status");
var statusDotEl = requireElement("status-dot");
var specPathEl = requireElement("spec-path");
var tweakCountEl = requireElement("tweak-count");
var diagnosticsEl = requireElement("diagnostics");
var tweakPanelEl = requireElement("tweak-panel");
var pageSelectorHostEl = requireElement("page-selector-host");
var previewContainerEl = requireElement("preview-container");
var previewFrameEl = requireElement("preview-frame");
var prevPageButtonEl = requireElement("prev-page");
var nextPageButtonEl = requireElement("next-page");
var zoomButtonEls = Array.from(document.querySelectorAll("[data-zoom-mode]"));
var pageSelectorTriggerEl = null;
var pageSelectorMenuEl = null;
function requireElement(id) {
  const element = document.getElementById(id);
  if (!element) throw new Error(`missing playground element #${id}`);
  return element;
}
function setStatus(message, kind = "idle") {
  statusEl.textContent = message;
  statusDotEl.dataset.state = kind;
  if (kind === "ok") {
    if (savedPulseTimer) clearTimeout(savedPulseTimer);
    savedPulseTimer = setTimeout(() => {
      statusDotEl.dataset.state = "idle";
    }, 1600);
  }
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
  if (scrollIntoView) suppressObserverUntil = Date.now() + 600;
  renderPageSelector();
  updateSelectedPageMarker(scrollIntoView);
}
function renderPageSelector() {
  const pages = playgroundState?.pages || [];
  pageSelectorHostEl.innerHTML = "";
  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "page-selector-trigger";
  trigger.id = "page-selector-trigger";
  trigger.disabled = pages.length === 0;
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");
  const current = pages[selectedPageIndex];
  const total = pages.length;
  const indexLabel = total ? `${pad2(selectedPageIndex + 1)} / ${pad2(total)}` : "\u2014";
  const indexParts = indexLabel.split(" / ");
  const indexSpan = document.createElement("span");
  indexSpan.className = "pst-index";
  indexSpan.textContent = indexParts[0];
  const sepSpan = document.createElement("span");
  sepSpan.className = "pst-sep";
  sepSpan.textContent = ` / `;
  const totalSpan = document.createElement("span");
  totalSpan.className = "pst-total";
  totalSpan.textContent = indexParts[1] || "";
  trigger.append(indexSpan, sepSpan, totalSpan);
  if (current) {
    const nameSpan = document.createElement("span");
    nameSpan.className = "pst-name";
    nameSpan.textContent = current.filename;
    nameSpan.title = current.filename;
    trigger.append(nameSpan);
  }
  const caret = document.createElement("span");
  caret.className = "pst-caret";
  caret.innerHTML = '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M6 9l6 6 6-6"/></svg>';
  trigger.append(caret);
  const menu = document.createElement("div");
  menu.className = "page-selector-menu";
  menu.setAttribute("role", "listbox");
  menu.id = "page-selector-menu";
  pages.forEach((page, index) => {
    const option = document.createElement("button");
    option.type = "button";
    option.className = "page-selector-option";
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", String(index === selectedPageIndex));
    option.dataset.index = String(index);
    const optIndex = document.createElement("span");
    optIndex.className = "pso-index";
    optIndex.textContent = pad2(page.pageNumber);
    const optName = document.createElement("span");
    optName.className = "pso-name";
    optName.textContent = page.filename;
    option.append(optIndex, optName);
    option.addEventListener("click", () => {
      selectPage(index, true);
      closePageSelector();
    });
    menu.appendChild(option);
  });
  trigger.addEventListener("click", () => {
    if (trigger.getAttribute("aria-expanded") === "true") {
      closePageSelector();
    } else {
      openPageSelector();
    }
  });
  pageSelectorHostEl.append(trigger, menu);
  pageSelectorTriggerEl = trigger;
  pageSelectorMenuEl = menu;
  prevPageButtonEl.disabled = pages.length === 0 || selectedPageIndex <= 0;
  nextPageButtonEl.disabled = pages.length === 0 || selectedPageIndex >= pages.length - 1;
}
function pad2(n) {
  return n < 10 ? `0${n}` : String(n);
}
function openPageSelector() {
  if (!pageSelectorTriggerEl || !pageSelectorMenuEl) return;
  pageSelectorTriggerEl.setAttribute("aria-expanded", "true");
  pageSelectorMenuEl.classList.add("is-open");
  document.addEventListener("click", outsidePageSelectorClick, true);
  document.addEventListener("keydown", pageSelectorKeydown);
  const selected = pageSelectorMenuEl.querySelector('[aria-selected="true"]');
  if (selected) selected.scrollIntoView({ block: "nearest" });
}
function closePageSelector() {
  if (!pageSelectorTriggerEl || !pageSelectorMenuEl) return;
  pageSelectorTriggerEl.setAttribute("aria-expanded", "false");
  pageSelectorMenuEl.classList.remove("is-open");
  document.removeEventListener("click", outsidePageSelectorClick, true);
  document.removeEventListener("keydown", pageSelectorKeydown);
}
function outsidePageSelectorClick(event) {
  if (!pageSelectorHostEl.contains(event.target)) closePageSelector();
}
function pageSelectorKeydown(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    closePageSelector();
    pageSelectorTriggerEl?.focus();
  }
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
function disconnectPageObserver() {
  if (pageObserver) {
    pageObserver.disconnect();
    pageObserver = null;
  }
}
function attachPageObserver() {
  disconnectPageObserver();
  if (!("IntersectionObserver" in window)) return;
  const sheets = Array.from(previewFrameEl.querySelectorAll(".page-sheet"));
  if (!sheets.length) return;
  pageObserver = new IntersectionObserver(
    (entries) => {
      if (Date.now() < suppressObserverUntil) return;
      let bestIndex = -1;
      let bestRatio = 0;
      for (const entry of entries) {
        if (entry.isIntersecting && entry.intersectionRatio > bestRatio) {
          const idx = Number(entry.target.dataset.pageIndex);
          if (!Number.isNaN(idx)) {
            bestRatio = entry.intersectionRatio;
            bestIndex = idx;
          }
        }
      }
      if (bestIndex >= 0 && bestIndex !== selectedPageIndex) {
        selectedPageIndex = bestIndex;
        renderPageSelector();
        updateSelectedPageMarker(false);
      }
    },
    {
      root: previewContainerEl,
      threshold: [0.25, 0.5, 0.75],
      rootMargin: "-20% 0px -20% 0px"
    }
  );
  for (const sheet of sheets) pageObserver.observe(sheet);
}
function renderPreview() {
  const pages = playgroundState?.pages || [];
  disconnectPageObserver();
  previewFrameEl.innerHTML = "";
  previewContainerEl.dataset.zoom = zoomMode;
  if (isLoadingState) {
    previewFrameEl.appendChild(emptyState("Rendering\u2026", "Folio is preparing your document."));
    return;
  }
  if (!pages.length) {
    const message = playgroundState?.diagnostics?.length ? "Fix the diagnostics on the right and reload." : "No rendered pages are available for this document.";
    previewFrameEl.appendChild(emptyState("No pages rendered", message));
    return;
  }
  pages.forEach((page, index) => {
    const sheet = document.createElement("section");
    sheet.className = "page-sheet";
    sheet.dataset.pageIndex = String(index);
    sheet.dataset.pageId = page.pageId;
    sheet.tabIndex = -1;
    sheet.setAttribute("aria-label", `Page ${page.pageNumber} \u2014 ${page.filename}`);
    sheet.innerHTML = page.svg;
    previewFrameEl.appendChild(sheet);
  });
  applyLiveCssVars();
  updateSelectedPageMarker(false);
  attachPageObserver();
}
function updateSelectedPageMarker(scrollIntoView) {
  const sheets = Array.from(previewFrameEl.querySelectorAll(".page-sheet"));
  if (scrollIntoView) {
    const target = sheets[selectedPageIndex];
    if (target) target.scrollIntoView({ block: "start", behavior: "smooth" });
  }
  if (pageSelectorTriggerEl) {
    const indexEl = pageSelectorTriggerEl.querySelector(".pst-index");
    if (indexEl) indexEl.textContent = pad2(selectedPageIndex + 1);
    const nameEl = pageSelectorTriggerEl.querySelector(".pst-name");
    const current = playgroundState?.pages[selectedPageIndex];
    if (nameEl && current) {
      nameEl.textContent = current.filename;
      nameEl.title = current.filename;
    }
  }
  if (pageSelectorMenuEl) {
    pageSelectorMenuEl.querySelectorAll(".page-selector-option").forEach((opt) => {
      opt.setAttribute("aria-selected", String(Number(opt.dataset.index) === selectedPageIndex));
    });
  }
  prevPageButtonEl.disabled = currentPageCount() === 0 || selectedPageIndex <= 0;
  nextPageButtonEl.disabled = currentPageCount() === 0 || selectedPageIndex >= currentPageCount() - 1;
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
function unitForKind(kind) {
  if (kind === "size_pt" || kind === "letter_spacing") return "pt";
  if (kind === "size_mm") return "mm";
  if (kind === "opacity") return "\u03B1";
  if (kind === "stroke_width") return "px";
  return "";
}
function normalizeInputValue(tweak, value) {
  if (NUMERIC_KINDS.has(tweak.kind) && value !== "") return Number(value);
  return value;
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
  tweakCountEl.textContent = String(tweaks.length);
  if (!tweaks.length) {
    const empty = emptyState(
      "No approved tweaks",
      "This document renders, but it has not declared any tweakable values yet. Add an `approve` block to expose controls."
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
  wrapper.dataset.kind = tweak.kind;
  const head = document.createElement("div");
  head.className = "tweak-control-head";
  const label = document.createElement("label");
  label.textContent = tweak.label || tweak.name || tweak.key;
  label.htmlFor = `tweak-${safeId(tweak.key)}`;
  const meta = document.createElement("div");
  meta.className = "tweak-meta";
  const keySpan = document.createElement("span");
  keySpan.className = "tm-key";
  keySpan.textContent = tweak.key;
  const sep1 = document.createElement("span");
  sep1.className = "tm-sep";
  sep1.textContent = "\xB7";
  const kindSpan = document.createElement("span");
  kindSpan.className = "tm-kind";
  kindSpan.textContent = tweak.kind;
  const sep2 = document.createElement("span");
  sep2.className = "tm-sep";
  sep2.textContent = "\xB7";
  const modeSpan = document.createElement("span");
  modeSpan.className = "tm-mode";
  modeSpan.dataset.mode = tweak.mode;
  modeSpan.textContent = tweak.mode;
  meta.append(keySpan, sep1, kindSpan, sep2, modeSpan);
  head.append(label, meta);
  wrapper.appendChild(head);
  const initialValue = String(
    draftValues[tweak.key] ?? playgroundState?.values[tweak.key] ?? tweak.value ?? tweak.default ?? ""
  );
  if (CHOICE_KINDS.has(tweak.kind) && Array.isArray(tweak.options)) {
    wrapper.appendChild(renderSelectControl(tweak, label.htmlFor, initialValue));
  } else if (tweak.kind === "color") {
    wrapper.appendChild(renderColorControl(tweak, label.htmlFor, initialValue));
  } else if (NUMERIC_KINDS.has(tweak.kind) && tweak.min !== null && tweak.min !== void 0 && tweak.max !== null && tweak.max !== void 0) {
    wrapper.appendChild(renderSliderControl(tweak, label.htmlFor, initialValue));
  } else {
    wrapper.appendChild(renderTextOrNumberControl(tweak, label.htmlFor, initialValue));
  }
  const status = document.createElement("div");
  status.id = `${label.htmlFor}-status`;
  status.className = "control-status";
  status.setAttribute("aria-live", "polite");
  status.textContent = "Saved";
  const diagnostic = document.createElement("div");
  diagnostic.id = `${label.htmlFor}-diagnostic`;
  diagnostic.className = "control-diagnostic";
  wrapper.append(status, diagnostic);
  return wrapper;
}
function renderTextOrNumberControl(tweak, id, initial) {
  const inputBox = document.createElement("div");
  inputBox.className = "tweak-input";
  const input = document.createElement("input");
  input.type = NUMERIC_KINDS.has(tweak.kind) ? "number" : "text";
  if (input.type === "number") {
    input.step = tweak.kind === "opacity" ? "0.01" : "0.1";
    if (tweak.min !== null && tweak.min !== void 0) input.min = String(tweak.min);
    if (tweak.max !== null && tweak.max !== void 0) input.max = String(tweak.max);
  }
  input.id = id;
  input.value = initial;
  input.addEventListener("input", () => handleTweakInput(tweak, input.value));
  input.addEventListener("change", () => handleTweakInput(tweak, input.value));
  inputBox.appendChild(input);
  const unit = unitForKind(tweak.kind);
  if (unit) {
    const u = document.createElement("span");
    u.className = "tweak-unit";
    u.textContent = unit;
    inputBox.appendChild(u);
  }
  return inputBox;
}
function renderSliderControl(tweak, id, initial) {
  const wrapper = document.createElement("div");
  wrapper.className = "tweak-slider";
  const range = document.createElement("input");
  range.type = "range";
  range.min = String(tweak.min);
  range.max = String(tweak.max);
  range.step = tweak.kind === "opacity" ? "0.01" : "0.1";
  range.value = initial;
  range.id = id;
  range.setAttribute("aria-label", tweak.label || tweak.name || tweak.key);
  setRangeProgress(range);
  const inputBox = document.createElement("div");
  inputBox.className = "tweak-input";
  const numberInput = document.createElement("input");
  numberInput.type = "number";
  numberInput.step = range.step;
  numberInput.min = String(tweak.min);
  numberInput.max = String(tweak.max);
  numberInput.value = initial;
  numberInput.setAttribute("aria-label", `${tweak.label || tweak.name || tweak.key} value`);
  inputBox.appendChild(numberInput);
  const unit = unitForKind(tweak.kind);
  if (unit) {
    const u = document.createElement("span");
    u.className = "tweak-unit";
    u.textContent = unit;
    inputBox.appendChild(u);
  }
  range.addEventListener("input", () => {
    numberInput.value = range.value;
    setRangeProgress(range);
    handleTweakInput(tweak, range.value);
  });
  numberInput.addEventListener("input", () => {
    range.value = numberInput.value;
    setRangeProgress(range);
    handleTweakInput(tweak, numberInput.value);
  });
  numberInput.addEventListener("change", () => handleTweakInput(tweak, numberInput.value));
  wrapper.append(range, inputBox);
  return wrapper;
}
function setRangeProgress(range) {
  const min = Number(range.min);
  const max = Number(range.max);
  const value = Number(range.value);
  if (!Number.isFinite(min) || !Number.isFinite(max) || max === min) return;
  const pct = Math.max(0, Math.min(1, (value - min) / (max - min))) * 100;
  range.style.setProperty("--track-progress", `${pct}%`);
}
function renderColorControl(tweak, id, initial) {
  const wrapper = document.createElement("div");
  wrapper.className = "tweak-color";
  const swatchLabel = document.createElement("label");
  swatchLabel.className = "tweak-swatch";
  swatchLabel.style.setProperty("--swatch-color", initial || "#888");
  swatchLabel.setAttribute("aria-label", `Pick color for ${tweak.label || tweak.name || tweak.key}`);
  const colorInput = document.createElement("input");
  colorInput.type = "color";
  colorInput.value = isHexColor(initial) ? initial : "#888888";
  colorInput.id = id;
  swatchLabel.appendChild(colorInput);
  const inputBox = document.createElement("div");
  inputBox.className = "tweak-input";
  const hexInput = document.createElement("input");
  hexInput.type = "text";
  hexInput.value = initial;
  hexInput.spellcheck = false;
  hexInput.setAttribute("aria-label", `${tweak.label || tweak.name || tweak.key} hex value`);
  inputBox.appendChild(hexInput);
  colorInput.addEventListener("input", () => {
    hexInput.value = colorInput.value;
    swatchLabel.style.setProperty("--swatch-color", colorInput.value);
    handleTweakInput(tweak, colorInput.value);
  });
  hexInput.addEventListener("input", () => {
    if (isHexColor(hexInput.value)) {
      colorInput.value = hexInput.value;
      swatchLabel.style.setProperty("--swatch-color", hexInput.value);
    }
    handleTweakInput(tweak, hexInput.value);
  });
  wrapper.append(swatchLabel, inputBox);
  return wrapper;
}
function isHexColor(value) {
  return /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(value);
}
function renderSelectControl(tweak, id, initial) {
  const wrapper = document.createElement("div");
  wrapper.className = "tweak-select";
  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "tweak-select-trigger";
  trigger.id = id;
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");
  const valueSpan = document.createElement("span");
  valueSpan.className = "tst-value";
  valueSpan.textContent = initial || "\u2014";
  const caret = document.createElement("span");
  caret.className = "tst-caret";
  caret.innerHTML = '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M6 9l6 6 6-6"/></svg>';
  trigger.append(valueSpan, caret);
  const menu = document.createElement("div");
  menu.className = "tweak-select-menu";
  menu.setAttribute("role", "listbox");
  const options = tweak.options || [];
  for (const optionValue of options) {
    const opt = document.createElement("button");
    opt.type = "button";
    opt.className = "tweak-select-option";
    opt.setAttribute("role", "option");
    opt.setAttribute("aria-selected", String(optionValue === initial));
    opt.textContent = optionValue;
    opt.addEventListener("click", () => {
      valueSpan.textContent = optionValue;
      menu.querySelectorAll(".tweak-select-option").forEach((o) => {
        o.setAttribute("aria-selected", String(o.textContent === optionValue));
      });
      closeSelect();
      handleTweakInput(tweak, optionValue);
    });
    menu.appendChild(opt);
  }
  function openSelect() {
    trigger.setAttribute("aria-expanded", "true");
    menu.classList.add("is-open");
    document.addEventListener("click", outside, true);
    document.addEventListener("keydown", esc);
  }
  function closeSelect() {
    trigger.setAttribute("aria-expanded", "false");
    menu.classList.remove("is-open");
    document.removeEventListener("click", outside, true);
    document.removeEventListener("keydown", esc);
  }
  function outside(event) {
    if (!wrapper.contains(event.target)) closeSelect();
  }
  function esc(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeSelect();
      trigger.focus();
    }
  }
  trigger.addEventListener("click", () => {
    if (trigger.getAttribute("aria-expanded") === "true") closeSelect();
    else openSelect();
  });
  wrapper.append(trigger, menu);
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
function renderTopMeta() {
  if (!playgroundState) {
    specPathEl.textContent = "\u2014";
    specPathEl.title = "";
    return;
  }
  const path = playgroundState.specPath || "\u2014";
  const segments = path.split("/").filter(Boolean);
  const shortened = segments.length > 2 ? `\u2026/${segments.slice(-2).join("/")}` : path;
  specPathEl.textContent = shortened;
  specPathEl.title = path;
}
function renderAll() {
  renderTopMeta();
  renderPageSelector();
  renderZoomControls();
  renderPreview();
  renderControls();
  displayDiagnostics(playgroundState?.diagnostics || []);
  if (isLoadingState) {
    setStatus("Loading\u2026", "loading");
  } else if (playgroundState?.diagnostics?.some((d) => d.severity === "error")) {
    setStatus(`${playgroundState.diagnostics.length} diagnostic(s)`, "error");
  } else if (playgroundState?.tweaks?.length) {
    setStatus(`${playgroundState.tweaks.length} tweak${playgroundState.tweaks.length === 1 ? "" : "s"} ready`, "ok");
  } else {
    setStatus("Ready \xB7 no tweaks declared", "idle");
  }
}
function schedulePatch(tweak) {
  if (pendingTimers.has(tweak.key)) clearTimeout(pendingTimers.get(tweak.key));
  const timer = setTimeout(() => patchTweak(tweak), DEBOUNCE_MS);
  pendingTimers.set(tweak.key, timer);
  const update = pendingStatus(tweak.key);
  update.timer = timer;
  setPendingStatus(tweak.key, "pending", "Pending");
}
async function patchTweak(tweak) {
  pendingTimers.delete(tweak.key);
  setPendingStatus(tweak.key, "saving", tweak.mode === "live" ? "Saving" : "Rerendering");
  setStatus(tweak.mode === "live" ? "Saving tweak\u2026" : "Rendering preview\u2026", "saving");
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
      setPendingStatus(tweak.key, "error", "Invalid");
      setStatus("Update rejected", "error");
      return;
    }
    mergeState(payload);
    controlDiagnostics.delete(tweak.key);
    setPendingStatus(tweak.key, "saved", "Saved");
    renderAll();
  } catch (error) {
    displayDiagnostics([{ severity: "error", key: tweak.key, message: String(error) }]);
    setPendingStatus(tweak.key, "error", "Failed");
    setStatus("Update failed", "error");
  }
}
function handleTweakInput(tweak, rawValue) {
  const value = normalizeInputValue(tweak, rawValue);
  draftValues[tweak.key] = value;
  controlDiagnostics.delete(tweak.key);
  if (tweak.mode === "live" && tweak.cssVar) {
    previewContainerEl.style.setProperty(tweak.cssVar, liveCssValue(tweak, value));
    setStatus("Preview updated \xB7 saving", "saving");
  } else {
    setStatus("Awaiting rerender\u2026", "saving");
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
      setStatus("Failed to render state", "error");
      return;
    }
    mergeState(state);
    isLoadingState = false;
    renderAll();
  } catch (error) {
    playgroundState = { specPath: "", valuesPath: "", pages: [], tweaks: [], values: {}, diagnostics: [{ severity: "error", key: null, message: `Failed to load state: ${error}` }] };
    isLoadingState = false;
    renderAll();
    setStatus("Failed to load state", "error");
  }
}
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
