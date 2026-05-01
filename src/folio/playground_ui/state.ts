// Centralized reactive state for the playground UI.
//
// One `createPlaygroundStore()` instance owns all signals; components
// import the store object from here and read/write specific signals
// directly. There is no global module-level mutable state.

import { createSignal } from "solid-js";

import type {
  Diagnostic,
  PlaygroundState,
  PlaygroundTweak,
  ResetTweakRequest,
} from "./api.generated";
import { fetchState, patchTweakValue, resetTweaks } from "./api";

export type UpdateStatus = "idle" | "pending" | "saving" | "saved" | "error";
export type ZoomMode = "fit-width" | "fit-page" | "actual-size";
export type GlobalStatus = "idle" | "loading" | "saving" | "ok" | "error";

export interface PendingUpdate {
  status: UpdateStatus;
  message: string;
}

const NUMERIC_KINDS = new Set([
  "size_pt",
  "size_mm",
  "opacity",
  "letter_spacing",
  "stroke_width",
]);
const CHOICE_KINDS = new Set(["choice", "preset", "font_choice"]);
const DEBOUNCE_MS = 250;

export function isNumericKind(kind: string): boolean {
  return NUMERIC_KINDS.has(kind);
}

export function isChoiceKind(kind: string): boolean {
  return CHOICE_KINDS.has(kind);
}

export function liveCssValue(tweak: PlaygroundTweak, value: unknown): string {
  if (value === null || value === undefined) return "";
  if (tweak.kind === "size_pt" || tweak.kind === "letter_spacing") return `${value}pt`;
  if (tweak.kind === "size_mm") return `${value}mm`;
  return String(value);
}

export function unitForKind(kind: string): string {
  if (kind === "size_pt" || kind === "letter_spacing") return "pt";
  if (kind === "size_mm") return "mm";
  if (kind === "opacity") return "α";
  if (kind === "stroke_width") return "px";
  return "";
}

export function normalizeInputValue(
  tweak: PlaygroundTweak,
  value: string,
): string | number {
  if (NUMERIC_KINDS.has(tweak.kind) && value !== "") return Number(value);
  return value;
}

export function isHexColor(value: string): boolean {
  return /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(value);
}

export function safeId(value: string): string {
  return value.replace(/[^a-z0-9_-]/gi, "-");
}

export function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

export interface PlaygroundStore {
  state: () => PlaygroundState | null;
  draftValues: () => Record<string, unknown>;
  pendingUpdates: () => Map<string, PendingUpdate>;
  controlDiagnostics: () => Map<string, string>;
  selectedPageIndex: () => number;
  zoomMode: () => ZoomMode;
  globalStatus: () => { state: GlobalStatus; text: string };
  isLoading: () => boolean;

  loadState: () => Promise<void>;
  setDraftValue: (key: string, value: unknown) => void;
  setSelectedPageIndex: (index: number) => void;
  setZoomMode: (mode: ZoomMode) => void;
  // Mark a tweak as ready to commit. The actual PATCH is debounced so
  // rapid commits (e.g. each keystroke in a number field) coalesce.
  // Drag-style inputs should NOT call this on every input event; only on
  // a discrete release event such as ``change``.
  commitTweak: (tweak: PlaygroundTweak) => void;
  resetTweaks: (request: ResetTweakRequest) => Promise<void>;
}

export function createPlaygroundStore(): PlaygroundStore {
  const [state, setState] = createSignal<PlaygroundState | null>(null);
  const [draftValues, setDraftValues] = createSignal<Record<string, unknown>>({});
  const [pendingUpdates, setPendingUpdates] = createSignal<Map<string, PendingUpdate>>(
    new Map(),
  );
  const [controlDiagnostics, setControlDiagnostics] = createSignal<Map<string, string>>(
    new Map(),
  );
  const [selectedPageIndex, setSelectedPageIndex] = createSignal(0);
  const [zoomMode, setZoomMode] = createSignal<ZoomMode>("fit-width");
  const [globalStatus, setGlobalStatus] = createSignal<{
    state: GlobalStatus;
    text: string;
  }>({ state: "idle", text: "Loading tweak state…" });
  const [isLoading, setIsLoading] = createSignal(true);

  const debounceTimers = new Map<string, ReturnType<typeof setTimeout>>();
  let savedPulseTimer: ReturnType<typeof setTimeout> | null = null;

  function setStatus(text: string, kind: GlobalStatus): void {
    setGlobalStatus({ state: kind, text });
    if (kind === "ok") {
      if (savedPulseTimer) clearTimeout(savedPulseTimer);
      savedPulseTimer = setTimeout(() => {
        setGlobalStatus((prev) => (prev.state === "ok" ? { state: "idle", text: prev.text } : prev));
      }, 1600);
    }
  }

  function setPendingStatus(key: string, status: UpdateStatus, message: string): void {
    setPendingUpdates((prev) => {
      const next = new Map(prev);
      next.set(key, { status, message });
      return next;
    });
  }

  function mergeFreshState(next: PlaygroundState): void {
    setState(next);
    if (selectedPageIndex() >= next.pages.length) setSelectedPageIndex(0);
    setDraftValues((prev) => {
      const merged = { ...prev };
      for (const tweak of next.tweaks) {
        if (!(tweak.key in merged)) {
          merged[tweak.key] = next.values[tweak.key] ?? tweak.value ?? tweak.default;
        }
      }
      return merged;
    });
    setControlDiagnostics(diagnosticsByKey(next.diagnostics));
    refreshGlobalStatusFromDiagnostics(next);
  }

  function refreshGlobalStatusFromDiagnostics(next: PlaygroundState): void {
    if (next.diagnostics.some((d) => d.severity === "error")) {
      setStatus(`${next.diagnostics.length} diagnostic(s)`, "error");
    } else if (next.tweaks.length) {
      setStatus(
        `${next.tweaks.length} tweak${next.tweaks.length === 1 ? "" : "s"} ready`,
        "ok",
      );
    } else {
      setStatus("Ready · no tweaks declared", "idle");
    }
  }

  async function loadState(): Promise<void> {
    setIsLoading(true);
    setStatus("Loading…", "loading");
    try {
      const next = await fetchState();
      mergeFreshState(next);
      setIsLoading(false);
    } catch (error: unknown) {
      const payload = (error as { payload?: { diagnostics?: Diagnostic[] } }).payload;
      const diagnostics: Diagnostic[] = payload?.diagnostics || [
        { severity: "error", key: null, message: `Failed to load state: ${error}` },
      ];
      setState({
        specPath: "",
        valuesPath: "",
        pages: [],
        tweaks: [],
        values: {},
        diagnostics,
      });
      setIsLoading(false);
      setStatus("Failed to load state", "error");
    }
  }

  function setDraftValue(key: string, value: unknown): void {
    setDraftValues((prev) => ({ ...prev, [key]: value }));
    setControlDiagnostics((prev) => {
      if (!prev.has(key)) return prev;
      const next = new Map(prev);
      next.delete(key);
      return next;
    });
  }

  function commitTweak(tweak: PlaygroundTweak): void {
    const existing = debounceTimers.get(tweak.key);
    if (existing) clearTimeout(existing);
    const timer = setTimeout(() => {
      void runPatch(tweak);
    }, DEBOUNCE_MS);
    debounceTimers.set(tweak.key, timer);
    setPendingStatus(tweak.key, "pending", "Pending");
    setStatus(
      tweak.mode === "live" ? "Preview updated · saving" : "Awaiting rerender…",
      "saving",
    );
  }

  async function runPatch(tweak: PlaygroundTweak): Promise<void> {
    debounceTimers.delete(tweak.key);
    setPendingStatus(
      tweak.key,
      "saving",
      tweak.mode === "live" ? "Saving" : "Rerendering",
    );
    setStatus(
      tweak.mode === "live" ? "Saving tweak…" : "Rendering preview…",
      "saving",
    );
    try {
      const next = await patchTweakValue(tweak.key, draftValues()[tweak.key]);
      mergeFreshState(next);
      setPendingStatus(tweak.key, "saved", "Saved");
    } catch (error: unknown) {
      const payload = (error as { payload?: { diagnostics?: Diagnostic[] } }).payload;
      const diagnostics: Diagnostic[] = payload?.diagnostics || [
        { severity: "error", key: tweak.key, message: String(error) },
      ];
      setControlDiagnostics(diagnosticsByKey(diagnostics));
      setState((prev) =>
        prev ? { ...prev, diagnostics } : prev,
      );
      setPendingStatus(tweak.key, "error", "Invalid");
      setStatus("Update rejected", "error");
    }
  }

  async function resetTweaksAction(request: ResetTweakRequest): Promise<void> {
    setStatus(
      request.scope === "all"
        ? "Resetting all tweaks…"
        : request.scope === "group"
        ? `Resetting ${request.group}…`
        : `Resetting ${request.key}…`,
      "saving",
    );
    try {
      const next = await resetTweaks(request);
      // Drop drafts for affected keys so the merge picks up the
      // freshly-resolved value instead of the in-flight draft.
      setDraftValues((prev) => {
        const out = { ...prev };
        for (const tweak of next.tweaks) {
          if (
            request.scope === "all" ||
            (request.scope === "group" && tweak.group === request.group) ||
            (request.scope === "tweak" && tweak.key === request.key)
          ) {
            delete out[tweak.key];
          }
        }
        return out;
      });
      setPendingUpdates((prev) => {
        const out = new Map(prev);
        for (const tweak of next.tweaks) {
          if (
            request.scope === "all" ||
            (request.scope === "group" && tweak.group === request.group) ||
            (request.scope === "tweak" && tweak.key === request.key)
          ) {
            out.delete(tweak.key);
          }
        }
        return out;
      });
      mergeFreshState(next);
      setStatus("Reset to defaults", "ok");
    } catch (error: unknown) {
      const payload = (error as { payload?: { diagnostics?: Diagnostic[] } }).payload;
      const diagnostics: Diagnostic[] = payload?.diagnostics || [
        { severity: "error", key: null, message: String(error) },
      ];
      setControlDiagnostics(diagnosticsByKey(diagnostics));
      setState((prev) => (prev ? { ...prev, diagnostics } : prev));
      setStatus("Reset rejected", "error");
    }
  }

  return {
    state,
    draftValues,
    pendingUpdates,
    controlDiagnostics,
    selectedPageIndex,
    zoomMode,
    globalStatus,
    isLoading,
    loadState,
    setDraftValue,
    setSelectedPageIndex,
    setZoomMode,
    commitTweak,
    resetTweaks: resetTweaksAction,
  };
}

function diagnosticsByKey(diagnostics: readonly Diagnostic[]): Map<string, string> {
  const byKey = new Map<string, string>();
  for (const diagnostic of diagnostics) {
    if (diagnostic.key) byKey.set(diagnostic.key, diagnostic.message);
  }
  return byKey;
}
