const API_STATE = "/api/state";
const API_TWEAKS = "/api/tweaks";
const DEBOUNCE_MS = 250;
const NUMERIC_KINDS = new Set(["size_pt", "size_mm", "opacity", "letter_spacing", "stroke_width"]);
const CHOICE_KINDS = new Set(["choice", "preset", "font_choice"]);

type Diagnostic = {
  severity: string;
  key: string | null;
  message: string;
};

type PlaygroundPage = {
  pageNumber: number;
  pageId: string;
  filename: string;
  svg: string;
};

type PlaygroundTweak = {
  key: string;
  group: string;
  name: string;
  kind: string;
  mode: string;
  value: unknown;
  default: unknown;
  cssVar: string;
  label: string | null;
  min: number | null;
  max: number | null;
  options: string[] | null;
};

type PlaygroundState = {
  specPath: string;
  valuesPath: string;
  pages: PlaygroundPage[];
  tweaks: PlaygroundTweak[];
  values: Record<string, unknown>;
  diagnostics: Diagnostic[];
};

type UpdateStatus = "idle" | "pending" | "saving" | "saved" | "error";
type ZoomMode = "fit-width" | "fit-page" | "actual-size";

type PendingUpdate = {
  timer: ReturnType<typeof setTimeout> | null;
  status: UpdateStatus;
  message: string;
};

let playgroundState: PlaygroundState | null = null;
let selectedPageIndex = 0;
let zoomMode: ZoomMode = "fit-width";
let isLoadingState = false;
const draftValues: Record<string, unknown> = {};
const pendingUpdates = new Map<string, PendingUpdate>();
const pendingTimers = new Map<string, ReturnType<typeof setTimeout>>();
const controlDiagnostics = new Map<string, string>();

const statusEl = requireElement("status");
const diagnosticsEl = requireElement("diagnostics");
const tweakPanelEl = requireElement("tweak-panel");
const pageSelectorEl = requireElement("page-selector") as HTMLSelectElement;
const previewContainerEl = requireElement("preview-container");
const previewFrameEl = requireElement("preview-frame");
const prevPageButtonEl = requireElement("prev-page") as HTMLButtonElement;
const nextPageButtonEl = requireElement("next-page") as HTMLButtonElement;
const zoomButtonEls = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-zoom-mode]"));

function requireElement(id: string): HTMLElement {
  const element = document.getElementById(id);
  if (!element) throw new Error(`missing playground element #${id}`);
  return element;
}

function setStatus(message: string): void {
  statusEl.textContent = message;
}

function pendingStatus(key: string): PendingUpdate {
  const current = pendingUpdates.get(key);
  if (current) return current;
  const next: PendingUpdate = { timer: null, status: "idle", message: "Saved" };
  pendingUpdates.set(key, next);
  return next;
}

function setPendingStatus(key: string, status: UpdateStatus, message: string): void {
  const update = pendingStatus(key);
  update.status = status;
  update.message = message;
  renderControlStatuses();
}

function diagnosticsByKey(diagnostics: Diagnostic[]): Map<string, string> {
  const byKey = new Map<string, string>();
  for (const diagnostic of diagnostics) {
    if (diagnostic.key) byKey.set(diagnostic.key, diagnostic.message);
  }
  return byKey;
}

function displayDiagnostics(diagnostics: Diagnostic[]): void {
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

function mergeState(nextState: PlaygroundState): void {
  playgroundState = nextState;
  if (selectedPageIndex >= nextState.pages.length) selectedPageIndex = 0;
  for (const tweak of nextState.tweaks) {
    if (!(tweak.key in draftValues)) {
      draftValues[tweak.key] = nextState.values[tweak.key] ?? tweak.value ?? tweak.default;
    }
  }
}

function currentPageCount(): number {
  return playgroundState?.pages.length || 0;
}

function currentPage(): PlaygroundPage | null {
  return playgroundState?.pages[selectedPageIndex] || null;
}

function selectPage(index: number, scrollIntoView = true): void {
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

function renderPageSelector(): void {
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

function liveCssValue(tweak: PlaygroundTweak, value: unknown): string {
  if (value === null || value === undefined) return "";
  if (tweak.kind === "size_pt" || tweak.kind === "letter_spacing") return `${value}pt`;
  if (tweak.kind === "size_mm") return `${value}mm`;
  return String(value);
}

function applyLiveCssVars(): void {
  if (!playgroundState) return;
  for (const tweak of playgroundState.tweaks) {
    if (tweak.mode === "live" && tweak.cssVar) {
      const value = draftValues[tweak.key] ?? playgroundState.values[tweak.key] ?? tweak.default;
      previewContainerEl.style.setProperty(tweak.cssVar, liveCssValue(tweak, value));
    }
  }
}

function renderPreview(): void {
  const pages = playgroundState?.pages || [];
  previewFrameEl.innerHTML = "";
  previewContainerEl.classList.toggle("is-empty", pages.length === 0);
  previewContainerEl.dataset.zoom = zoomMode;

  if (isLoadingState) {
    previewFrameEl.appendChild(emptyState("Loading rendered pages…", "The local server is preparing the playground state."));
    return;
  }

  if (!pages.length) {
    const message = playgroundState?.diagnostics?.length
      ? "The document did not render. Fix the diagnostics, then reload the playground."
      : "No rendered pages are available for this document.";
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

function updateSelectedPageCard(scrollIntoView: boolean): void {
  const cards = Array.from(previewFrameEl.querySelectorAll<HTMLElement>(".page-card"));
  cards.forEach((card, index) => {
    const selected = index === selectedPageIndex;
    card.classList.toggle("is-selected", selected);
    card.setAttribute("aria-pressed", String(selected));
    if (selected && scrollIntoView) card.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
  renderPageSelector();
}

function emptyState(title: string, detail: string): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "empty-state";
  const heading = document.createElement("h2");
  heading.textContent = title;
  const body = document.createElement("p");
  body.textContent = detail;
  wrapper.append(heading, body);
  return wrapper;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>'"]/g, (char) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    };
    return entities[char] || char;
  });
}

function controlInputType(tweak: PlaygroundTweak): string {
  if (tweak.kind === "color") return "color";
  if (NUMERIC_KINDS.has(tweak.kind)) return "number";
  return "text";
}

function normalizeInputValue(tweak: PlaygroundTweak, value: string): string | number {
  if (NUMERIC_KINDS.has(tweak.kind) && value !== "") return Number(value);
  return value;
}

function buildInput(tweak: PlaygroundTweak): HTMLInputElement | HTMLSelectElement {
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
    if (tweak.min !== null && tweak.min !== undefined) input.min = String(tweak.min);
    if (tweak.max !== null && tweak.max !== undefined) input.max = String(tweak.max);
  }
  return input;
}

function groupedTweaks(tweaks: PlaygroundTweak[]): Map<string, PlaygroundTweak[]> {
  const groups = new Map<string, PlaygroundTweak[]>();
  for (const tweak of tweaks) {
    const groupName = tweak.group || tweak.key.split(".")[0] || "Tweaks";
    const group = groups.get(groupName) || [];
    group.push(tweak);
    groups.set(groupName, group);
  }
  return groups;
}

function renderControls(): void {
  tweakPanelEl.innerHTML = "";
  const tweaks = playgroundState?.tweaks || [];
  if (!tweaks.length) {
    const empty = emptyState(
      "No approved tweaks",
      "This document renders successfully, but it has not declared any approved tweakable values yet. Page previews remain available for inspection.",
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

function renderControl(tweak: PlaygroundTweak): HTMLElement {
  const wrapper = document.createElement("article");
  wrapper.className = "tweak-control";
  wrapper.dataset.tweakKey = tweak.key;

  const label = document.createElement("label");
  label.textContent = tweak.label || tweak.name || tweak.key;
  label.htmlFor = `tweak-${safeId(tweak.key)}`;

  const meta = document.createElement("div");
  meta.className = "tweak-meta";
  meta.textContent = `${tweak.key} · ${tweak.kind} · ${tweak.mode}`;

  const row = document.createElement("div");
  row.className = "tweak-row";
  const input = buildInput(tweak);
  input.id = label.htmlFor;
  input.value = String(draftValues[tweak.key] ?? playgroundState?.values[tweak.key] ?? tweak.value ?? tweak.default ?? "");
  input.setAttribute("aria-describedby", `${input.id}-status ${input.id}-diagnostic`);
  input.addEventListener("input", () => handleTweakInput(tweak, input.value));
  input.addEventListener("change", () => handleTweakInput(tweak, input.value));
  row.appendChild(input);

  if (input instanceof HTMLInputElement && input.type === "number" && tweak.min !== null && tweak.min !== undefined && tweak.max !== null && tweak.max !== undefined) {
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

function renderControlStatuses(): void {
  document.querySelectorAll<HTMLElement>(".tweak-control").forEach((control) => {
    const key = control.dataset.tweakKey;
    if (!key) return;
    const status = control.querySelector<HTMLElement>(".control-status");
    const update = pendingUpdates.get(key);
    control.dataset.status = update?.status || "idle";
    if (status) status.textContent = update?.message || "Saved";
    const diagnostic = control.querySelector<HTMLElement>(".control-diagnostic");
    if (diagnostic && controlDiagnostics.has(key)) diagnostic.textContent = controlDiagnostics.get(key) || "";
    control.classList.toggle("is-invalid", controlDiagnostics.has(key));
  });
}

function safeId(value: string): string {
  return value.replace(/[^a-z0-9_-]/gi, "-");
}

function renderZoomControls(): void {
  previewContainerEl.dataset.zoom = zoomMode;
  for (const button of zoomButtonEls) {
    const active = button.dataset.zoomMode === zoomMode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  }
}

function renderAll(): void {
  renderPageSelector();
  renderZoomControls();
  renderPreview();
  renderControls();
  displayDiagnostics(playgroundState?.diagnostics || []);
  if (isLoadingState) setStatus("Loading playground state…");
  else if (playgroundState?.tweaks?.length) setStatus(`${playgroundState.tweaks.length} tweak(s) loaded.`);
  else setStatus("No tweaks declared. Page previews are still available.");
}

function schedulePatch(tweak: PlaygroundTweak): void {
  if (pendingTimers.has(tweak.key)) clearTimeout(pendingTimers.get(tweak.key));
  const timer = setTimeout(() => patchTweak(tweak), DEBOUNCE_MS);
  pendingTimers.set(tweak.key, timer);
  const update = pendingStatus(tweak.key);
  update.timer = timer;
  setPendingStatus(tweak.key, "pending", "Waiting to save…");
}

async function patchTweak(tweak: PlaygroundTweak): Promise<void> {
  pendingTimers.delete(tweak.key);
  setPendingStatus(tweak.key, "saving", tweak.mode === "live" ? "Saving…" : "Saving and rerendering…");
  if (tweak.mode !== "live") setStatus("Rendering updated preview…");
  else setStatus("Saving tweak…");
  try {
    const response = await fetch(API_TWEAKS, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: tweak.key, value: draftValues[tweak.key] }),
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

function handleTweakInput(tweak: PlaygroundTweak, rawValue: string): void {
  const value = normalizeInputValue(tweak, rawValue);
  draftValues[tweak.key] = value;
  controlDiagnostics.delete(tweak.key);
  if (tweak.mode === "live" && tweak.cssVar) {
    previewContainerEl.style.setProperty(tweak.cssVar, liveCssValue(tweak, value));
    setStatus("Preview updated. Saving…");
  } else {
    setStatus("Waiting to rerender…");
  }
  schedulePatch(tweak);
}

async function loadState(): Promise<void> {
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
    mergeState(state as PlaygroundState);
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
    zoomMode = (button.dataset.zoomMode as ZoomMode) || "fit-width";
    renderZoomControls();
  });
});

loadState();
