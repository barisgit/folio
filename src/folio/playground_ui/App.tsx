// Folio playground UI rendered with Solid.
//
// Component shape mirrors the prior vanilla-DOM implementation in
// ``main.ts`` (preserved in git history). Every CSS class name and ARIA
// attribute is carried over so the existing ``styles.css`` works
// unchanged. State lives in the store from ``state.ts``; this file is
// pure rendering.

import { Select } from "@kobalte/core/select";
import {
  For,
  Show,
  createEffect,
  createMemo,
  createSignal,
  onCleanup,
} from "solid-js";

import type { PlaygroundPage, PlaygroundTweak } from "./api.generated";
import {
  type PlaygroundStore,
  isChoiceKind,
  isHexColor,
  isNumericKind,
  liveCssValue,
  normalizeInputValue,
  safeId,
  unitForKind,
} from "./state";

interface AppProps {
  store: PlaygroundStore;
}

export function App(props: AppProps) {
  const { store } = props;

  // The previous DOM implementation grouped tweaks by the ``group`` field,
  // falling back to the first segment of the dotted key. We do the same
  // and keep insertion order so groups appear top-to-bottom in declaration
  // order, not alphabetical.
  const groupedTweaks = createMemo(() => {
    const groups = new Map<string, PlaygroundTweak[]>();
    const tweaks = store.state()?.tweaks || [];
    for (const tweak of tweaks) {
      const groupName = tweak.group || tweak.key.split(".")[0] || "Tweaks";
      const arr = groups.get(groupName) || [];
      arr.push(tweak);
      groups.set(groupName, arr);
    }
    return Array.from(groups.entries());
  });

  const globalDiagnostics = createMemo(() =>
    (store.state()?.diagnostics || []).filter((d) => !d.key),
  );

  const divergedTotal = createMemo(
    () => (store.state()?.tweaks || []).filter((t) => t.diverged).length,
  );

  const specFilename = createMemo(() => {
    const path = store.state()?.specPath || "";
    if (!path) return "—";
    const segments = path.split("/").filter(Boolean);
    return segments[segments.length - 1] || path;
  });

  // Group pages by document_id, preserving the order pages were emitted.
  // ``meta`` is a short page-size label (e.g. "a4" / "16:9") inferred from
  // width_mm × height_mm so the doc tree row can hint at format without
  // additional backend work.
  const groupedDocs = createMemo(() => {
    const docs = new Map<string, DocGroup>();
    const pages = store.state()?.pages || [];
    pages.forEach((page, index) => {
      const id = page.documentId || "document";
      let entry = docs.get(id);
      if (!entry) {
        entry = {
          id,
          label: page.documentLabel || id,
          meta: pageSizeLabel(page.widthMm, page.heightMm),
          pages: [],
        };
        docs.set(id, entry);
      }
      entry.pages.push({ index, page });
    });
    return Array.from(docs.values());
  });

  return (
    <main id="folio-playground">
      <Topbar
        store={store}
        specFilename={specFilename}
        divergedTotal={divergedTotal}
      />

      <DocTree store={store} groups={groupedDocs} />

      <Workspace store={store} />

      <aside class="panel" aria-label="Tweak controls">

        <ul
          class="diagnostics"
          aria-live="polite"
          aria-label="Playground diagnostics"
          hidden={globalDiagnostics().length === 0}
        >
          <For each={globalDiagnostics()}>
            {(diagnostic) => (
              <li class={`diagnostic diagnostic-${diagnostic.severity || "info"}`}>
                {diagnostic.message}
              </li>
            )}
          </For>
        </ul>

        <section class="tweak-panel" aria-label="Tweaks">
          <Show
            when={(store.state()?.tweaks.length ?? 0) > 0}
            fallback={
              <EmptyState
                class="inspector-empty"
                title="No approved tweaks"
                detail="This document renders, but it has not declared any tweakable values yet. Add an `approve` block to expose controls."
              />
            }
          >
            <For each={groupedTweaks()}>
              {([groupName, groupTweaks]) => {
                const divergedInGroup = () =>
                  groupTweaks.filter((t) => t.diverged).length;
                return (
                  <section
                    class="tweak-group"
                    aria-labelledby={`group-${safeId(groupName)}`}
                  >
                    <header class="tweak-group-head">
                      <h3 id={`group-${safeId(groupName)}`}>{groupName}</h3>
                      <Show when={divergedInGroup() > 0}>
                        <button
                          type="button"
                          class="reset-btn reset-btn-group"
                          onClick={() => {
                            void store.resetTweaks({
                              scope: "group",
                              group: groupName,
                            });
                          }}
                          title={`Reset ${divergedInGroup()} tweak(s) in ${groupName}`}
                        >
                          reset group
                        </button>
                      </Show>
                    </header>
                    <For each={groupTweaks}>
                      {(tweak) => <TweakControl tweak={tweak} store={store} />}
                    </For>
                  </section>
                );
              }}
            </For>
          </Show>
        </section>
      </aside>
    </main>
  );
}

interface DocGroup {
  id: string;
  label: string;
  meta: string;
  pages: { index: number; page: PlaygroundPage }[];
}

// Map a page width/height in millimetres to a short visual hint shown in
// the doc tree (e.g. "a4", "16:9"). Falls back to the raw dimensions
// rounded to the nearest mm.
function pageSizeLabel(widthMm: number, heightMm: number): string {
  const w = Math.round(widthMm);
  const h = Math.round(heightMm);
  // Common ISO/letter sizes in either orientation.
  const known: [number, number, string][] = [
    [210, 297, "a4"],
    [297, 420, "a3"],
    [148, 210, "a5"],
    [216, 279, "letter"],
  ];
  for (const [kw, kh, label] of known) {
    if ((w === kw && h === kh) || (w === kh && h === kw)) return label;
  }
  // Aspect-ratio sniff for broadcast/screen sizes.
  const long = Math.max(w, h);
  const short = Math.min(w, h);
  if (short > 0) {
    const ratio = long / short;
    if (Math.abs(ratio - 16 / 9) < 0.02) return "16:9";
    if (Math.abs(ratio - 4 / 3) < 0.02) return "4:3";
  }
  return `${w}×${h}mm`;
}

// Inline value display next to a tweak's label: "58 pt", "#445566",
// "calm", "40 mm". Trims trailing zeros for numeric values so 32.0 reads
// as ``32`` while 12.5 stays ``12.5``.
function formatTweakValue(tweak: PlaygroundTweak, raw: string): string {
  const unit = unitForKind(tweak.kind);
  if (isNumericKind(tweak.kind)) {
    const n = Number(raw);
    if (!Number.isFinite(n)) return raw;
    const formatted =
      tweak.kind === "opacity"
        ? n.toFixed(2).replace(/\.0+$/, "")
        : Number(n.toFixed(2)).toString();
    return unit ? `${formatted} ${unit}` : formatted;
  }
  return raw;
}

interface TopbarProps {
  store: PlaygroundStore;
  specFilename: () => string;
  divergedTotal: () => number;
}

interface DocTreeProps {
  store: PlaygroundStore;
  groups: () => DocGroup[];
}

// Left zone: nested doc tree (VS Code explorer pattern). When the spec
// returns a single document the chevron + meta are dropped so it reads as
// a flat page list. Clicking a page row scrolls the matching ``.page-sheet``
// into view via the same ``selectedPageIndex`` signal the workspace uses.
function DocTree(props: DocTreeProps) {
  const [collapsed, setCollapsed] = createSignal<Record<string, boolean>>({});

  function toggle(id: string): void {
    setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  function selectPage(index: number): void {
    props.store.setSelectedPageIndex(index);
    if (typeof document === "undefined") return;
    const root = document.querySelector<HTMLElement>(".page-stack");
    const sheets = root?.querySelectorAll<HTMLElement>(".page-sheet");
    sheets?.[index]?.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  const isFlat = () => props.groups().length <= 1;

  return (
    <aside class="doc-tree" aria-label="Document pages">
      <For each={props.groups()}>
        {(group) => {
          const open = () => !collapsed()[group.id];
          return (
            <section class="doc">
              <Show when={!isFlat()}>
                <button
                  type="button"
                  class="doc-row"
                  aria-expanded={open()}
                  onClick={() => toggle(group.id)}
                >
                  <span
                    class="doc-chevron"
                    classList={{ "is-open": open() }}
                    aria-hidden="true"
                  >
                    ▾
                  </span>
                  <span class="doc-name">{group.label}</span>
                  <span class="doc-meta">{group.meta}</span>
                </button>
              </Show>
              <Show when={open()}>
                <div class="doc-pages">
                  <For each={group.pages}>
                    {(entry) => {
                      const active = () =>
                        props.store.selectedPageIndex() === entry.index;
                      return (
                        <button
                          type="button"
                          class="page-row"
                          classList={{
                            "is-active": active(),
                            "is-flat": isFlat(),
                          }}
                          aria-current={active() ? "page" : undefined}
                          onClick={() => selectPage(entry.index)}
                        >
                          {pageRowLabel(entry.page.filename)}
                        </button>
                      );
                    }}
                  </For>
                </div>
              </Show>
            </section>
          );
        }}
      </For>
    </aside>
  );
}

// Page row label: drop a trailing ``.svg`` (the design rule says page
// rows show just the name, no extension), but keep any other extension a
// caller might use (e.g. ``cover.png``) so the row still identifies the
// page unambiguously.
function pageRowLabel(filename: string): string {
  return filename.replace(/\.svg$/i, "");
}

function Topbar(props: TopbarProps) {
  return (
    <header class="topbar" aria-label="Playground header">
      <div class="brand">
        <span class="brand-dot" aria-hidden="true" />
        <span class="brand-name">folio</span>
        <span class="brand-spec" title={props.store.state()?.specPath || ""}>
          {props.specFilename()}
        </span>
      </div>

      <div class="topbar-actions">
        <Show when={props.divergedTotal() > 0}>
          <button
            type="button"
            class="reset-all-link"
            onClick={() => void props.store.resetTweaks({ scope: "all" })}
            title={`Reset all ${props.divergedTotal()} edited tweak(s)`}
          >
            reset all
          </button>
        </Show>
        <span
          class="topbar-status"
          data-state={props.store.globalStatus().state}
          role="status"
          aria-live="polite"
        >
          {props.store.globalStatus().text}
        </span>
      </div>
    </header>
  );
}

interface WorkspaceProps {
  store: PlaygroundStore;
}

function Workspace(props: WorkspaceProps) {
  let previewContainerEl: HTMLDivElement | undefined;
  let previewFrameEl: HTMLDivElement | undefined;
  let pageObserver: IntersectionObserver | null = null;
  let suppressObserverUntil = 0;

  const pageCount = () => props.store.state()?.pages.length ?? 0;

  function selectPage(index: number, scrollIntoView = true): void {
    const count = pageCount();
    if (!count) {
      props.store.setSelectedPageIndex(0);
      return;
    }
    const clamped = Math.max(0, Math.min(index, count - 1));
    if (scrollIntoView) suppressObserverUntil = Date.now() + 600;
    props.store.setSelectedPageIndex(clamped);
    if (scrollIntoView && previewFrameEl) {
      const sheets = previewFrameEl.querySelectorAll<HTMLElement>(".page-sheet");
      sheets[clamped]?.scrollIntoView({ block: "start", behavior: "smooth" });
    }
  }

  // Apply live CSS variables whenever draft values or state change so
  // ``mode == "live"`` tweaks update the preview without a server round
  // trip.
  createEffect(() => {
    const state = props.store.state();
    const drafts = props.store.draftValues();
    if (!state || !previewContainerEl) return;
    for (const tweak of state.tweaks) {
      if (tweak.mode === "live" && tweak.cssVar) {
        const value = drafts[tweak.key] ?? state.values[tweak.key] ?? tweak.default;
        previewContainerEl.style.setProperty(tweak.cssVar, liveCssValue(tweak, value));
      }
    }
  });

  // Re-attach an IntersectionObserver every time pages change so scrolling
  // syncs the page selector.
  createEffect(() => {
    const _pages = props.store.state()?.pages;
    if (pageObserver) {
      pageObserver.disconnect();
      pageObserver = null;
    }
    if (!previewContainerEl || !previewFrameEl) return;
    if (!("IntersectionObserver" in window)) return;
    const sheets = Array.from(previewFrameEl.querySelectorAll<HTMLElement>(".page-sheet"));
    if (!sheets.length) return;
    pageObserver = new IntersectionObserver(
      (entries) => {
        if (Date.now() < suppressObserverUntil) return;
        let bestIndex = -1;
        let bestRatio = 0;
        for (const entry of entries) {
          if (entry.isIntersecting && entry.intersectionRatio > bestRatio) {
            const idx = Number((entry.target as HTMLElement).dataset.pageIndex);
            if (!Number.isNaN(idx)) {
              bestRatio = entry.intersectionRatio;
              bestIndex = idx;
            }
          }
        }
        if (bestIndex >= 0 && bestIndex !== props.store.selectedPageIndex()) {
          props.store.setSelectedPageIndex(bestIndex);
        }
      },
      {
        root: previewContainerEl,
        threshold: [0.25, 0.5, 0.75],
        rootMargin: "-20% 0px -20% 0px",
      },
    );
    for (const sheet of sheets) pageObserver.observe(sheet);
    void _pages;
  });

  onCleanup(() => {
    pageObserver?.disconnect();
    pageObserver = null;
  });

  function onPreviewKeydown(event: KeyboardEvent): void {
    if (event.key === "ArrowUp" || event.key === "PageUp") {
      event.preventDefault();
      selectPage(props.store.selectedPageIndex() - 1);
    }
    if (event.key === "ArrowDown" || event.key === "PageDown") {
      event.preventDefault();
      selectPage(props.store.selectedPageIndex() + 1);
    }
  }

  return (
    <section class="workspace" aria-label="Rendered document workspace">
      <div class="center-bar" aria-label="Document controls">
        <div class="zoom-segments" role="tablist" aria-label="Zoom mode">
          <For each={["fit-width", "fit-page", "actual-size"] as const}>
            {(mode) => {
              const labels: Record<typeof mode, string> = {
                "fit-width": "Width",
                "fit-page": "Page",
                "actual-size": "100%",
              };
              const titles: Record<typeof mode, string> = {
                "fit-width": "Fit to width",
                "fit-page": "Fit page in view",
                "actual-size": "100%",
              };
              const active = () => props.store.zoomMode() === mode;
              return (
                <button
                  type="button"
                  role="tab"
                  data-zoom-mode={mode}
                  aria-pressed={active()}
                  classList={{ "is-active": active() }}
                  title={titles[mode]}
                  onClick={() => props.store.setZoomMode(mode)}
                >
                  {labels[mode]}
                </button>
              );
            }}
          </For>
        </div>
      </div>

      <div
        ref={previewContainerEl}
        class="page-canvas"
        tabindex="0"
        aria-label="Scrollable document pages"
        data-zoom={props.store.zoomMode()}
        onKeyDown={onPreviewKeydown}
      >
        <div ref={previewFrameEl} class="page-stack">
          <Show
            when={!props.store.isLoading()}
            fallback={<EmptyState title="Rendering…" detail="Folio is preparing your document." />}
          >
            <Show
              when={(props.store.state()?.pages.length ?? 0) > 0}
              fallback={
                <EmptyState
                  title="No pages rendered"
                  detail={
                    (props.store.state()?.diagnostics.length ?? 0) > 0
                      ? "Fix the diagnostics on the right and reload."
                      : "No rendered pages are available for this document."
                  }
                />
              }
            >
              <For each={props.store.state()?.pages || []}>
                {(page, index) => (
                  <section
                    class="page-sheet"
                    data-page-index={index()}
                    data-page-id={page.pageId}
                    tabindex={-1}
                    aria-label={`Page ${page.pageNumber} — ${page.filename}`}
                    style={{
                      "--page-w-mm": String(page.widthMm),
                      "--page-h-mm": String(page.heightMm),
                      "aspect-ratio": `${page.widthMm} / ${page.heightMm}`,
                    }}
                    // SVG content arrives as trusted markup from the
                    // backend pipeline; innerHTML is intentional.
                    innerHTML={page.svg}
                  />
                )}
              </For>
            </Show>
          </Show>
        </div>
      </div>
    </section>
  );
}

interface TweakControlProps {
  tweak: PlaygroundTweak;
  store: PlaygroundStore;
}

function TweakControl(props: TweakControlProps) {
  const inputId = () => `tweak-${safeId(props.tweak.key)}`;

  const initialValue = () => {
    const draft = props.store.draftValues()[props.tweak.key];
    const stateValue = props.store.state()?.values[props.tweak.key];
    return String(
      draft ?? stateValue ?? props.tweak.value ?? props.tweak.default ?? "",
    );
  };

  const pendingMessage = () =>
    props.store.pendingUpdates().get(props.tweak.key)?.message || "Saved";
  const pendingStatus = () =>
    props.store.pendingUpdates().get(props.tweak.key)?.status || "idle";
  const diagnosticMessage = () =>
    props.store.controlDiagnostics().get(props.tweak.key) || "";
  const isInvalid = () => props.store.controlDiagnostics().has(props.tweak.key);

  // Drag-style inputs (slider, color picker) keep updating the live
  // preview via ``handleInput`` without hitting the server. The PATCH is
  // only scheduled by ``handleCommit`` on a discrete release event
  // (slider release, blur/Enter on a number/text field, color picker
  // close, dropdown selection) so a mid-drag pause never cancels the
  // ongoing gesture by replacing the DOM node from a server response.
  function handleInput(rawValue: string): void {
    const value = normalizeInputValue(props.tweak, rawValue);
    props.store.setDraftValue(props.tweak.key, value);
  }

  function handleCommit(rawValue: string): void {
    const value = normalizeInputValue(props.tweak, rawValue);
    props.store.setDraftValue(props.tweak.key, value);
    props.store.commitTweak(props.tweak);
  }

  return (
    <article
      class="tweak-control"
      data-tweak-key={props.tweak.key}
      data-kind={props.tweak.kind}
      data-status={pendingStatus()}
      classList={{ "is-invalid": isInvalid() }}
    >
      <div class="tweak-control-head">
        <label for={inputId()} class="tweak-name">
          {props.tweak.label || props.tweak.name || props.tweak.key}
        </label>
        <div class="tweak-head-right">
          <span class="tweak-value">{formatTweakValue(props.tweak, initialValue())}</span>
          <Show when={props.tweak.diverged}>
            <button
              type="button"
              class="reset-btn-tweak"
              onClick={() =>
                void props.store.resetTweaks({
                  scope: "tweak",
                  key: props.tweak.key,
                })
              }
              title="Reset to spec default"
              aria-label="Reset to spec default"
            >
              ↺
            </button>
          </Show>
        </div>
      </div>

      {(() => {
        const t = props.tweak;
        if (isChoiceKind(t.kind) && Array.isArray(t.options)) {
          return (
            <SelectControl
              tweak={t}
              id={inputId()}
              initial={initialValue()}
              onInput={handleInput}
              onCommit={handleCommit}
            />
          );
        }
        if (t.kind === "color") {
          return (
            <ColorControl
              tweak={t}
              id={inputId()}
              initial={initialValue()}
              onInput={handleInput}
              onCommit={handleCommit}
            />
          );
        }
        if (
          isNumericKind(t.kind) &&
          t.min !== null && t.min !== undefined &&
          t.max !== null && t.max !== undefined
        ) {
          return (
            <SliderControl
              tweak={t}
              id={inputId()}
              initial={initialValue()}
              onInput={handleInput}
              onCommit={handleCommit}
            />
          );
        }
        return (
          <TextNumberControl
            tweak={t}
            id={inputId()}
            initial={initialValue()}
            onInput={handleInput}
            onCommit={handleCommit}
          />
        );
      })()}

      <div class="control-status" aria-live="polite">{pendingMessage()}</div>
      <div class="control-diagnostic">{diagnosticMessage()}</div>
    </article>
  );
}

interface ControlBaseProps {
  tweak: PlaygroundTweak;
  id: string;
  initial: string;
  // Fires on every transient change (drag tick, keystroke). Updates the
  // local draft + live preview only.
  onInput: (raw: string) => void;
  // Fires on a discrete release/commit event (slider release, blur/Enter,
  // color picker close, option pick). Triggers the debounced PATCH.
  onCommit: (raw: string) => void;
}

function TextNumberControl(props: ControlBaseProps) {
  const isNumber = isNumericKind(props.tweak.kind);
  return (
    <div class="tweak-input">
      <input
        type={isNumber ? "number" : "text"}
        id={props.id}
        value={props.initial}
        step={isNumber ? (props.tweak.kind === "opacity" ? "0.01" : "0.1") : undefined}
        min={isNumber && props.tweak.min !== null && props.tweak.min !== undefined ? String(props.tweak.min) : undefined}
        max={isNumber && props.tweak.max !== null && props.tweak.max !== undefined ? String(props.tweak.max) : undefined}
        onInput={(e) => props.onInput(e.currentTarget.value)}
        onChange={(e) => props.onCommit(e.currentTarget.value)}
      />
      <Show when={unitForKind(props.tweak.kind)}>
        {(unit) => <span class="tweak-unit">{unit()}</span>}
      </Show>
    </div>
  );
}

function SliderControl(props: ControlBaseProps) {
  const [value, setValue] = createSignal(props.initial);
  const min = String(props.tweak.min);
  const max = String(props.tweak.max);
  const step = props.tweak.kind === "opacity" ? "0.01" : "0.1";

  const trackProgress = () => {
    const minNum = Number(min);
    const maxNum = Number(max);
    const v = Number(value());
    if (!Number.isFinite(minNum) || !Number.isFinite(maxNum) || maxNum === minNum) return "0%";
    const pct = Math.max(0, Math.min(1, (v - minNum) / (maxNum - minNum))) * 100;
    return `${pct}%`;
  };

  function preview(raw: string): void {
    setValue(raw);
    props.onInput(raw);
  }

  function commit(raw: string): void {
    setValue(raw);
    props.onCommit(raw);
  }

  return (
    <div class="tweak-slider">
      <input
        type="range"
        id={props.id}
        min={min}
        max={max}
        step={step}
        value={value()}
        aria-label={props.tweak.label || props.tweak.name || props.tweak.key}
        style={{ "--track-progress": trackProgress() }}
        onInput={(e) => preview(e.currentTarget.value)}
        onChange={(e) => commit(e.currentTarget.value)}
      />
      <div class="tweak-input">
        <input
          type="number"
          min={min}
          max={max}
          step={step}
          value={value()}
          aria-label={`${props.tweak.label || props.tweak.name || props.tweak.key} value`}
          onInput={(e) => preview(e.currentTarget.value)}
          onChange={(e) => commit(e.currentTarget.value)}
        />
        <Show when={unitForKind(props.tweak.kind)}>
          {(unit) => <span class="tweak-unit">{unit()}</span>}
        </Show>
      </div>
    </div>
  );
}

function ColorControl(props: ControlBaseProps) {
  const [hex, setHex] = createSignal(props.initial);
  const [pickerValue, setPickerValue] = createSignal(
    isHexColor(props.initial) ? props.initial : "#888888",
  );

  function onPickerInput(value: string): void {
    setPickerValue(value);
    setHex(value);
    props.onInput(value);
  }

  function onPickerCommit(value: string): void {
    setPickerValue(value);
    setHex(value);
    props.onCommit(value);
  }

  function onHexInput(value: string): void {
    setHex(value);
    if (isHexColor(value)) setPickerValue(value);
    props.onInput(value);
  }

  function onHexCommit(value: string): void {
    setHex(value);
    if (isHexColor(value)) setPickerValue(value);
    props.onCommit(value);
  }

  return (
    <div class="tweak-color">
      <label
        class="tweak-swatch"
        style={{ "--swatch-color": isHexColor(hex()) ? hex() : "#888" }}
        aria-label={`Pick color for ${props.tweak.label || props.tweak.name || props.tweak.key}`}
      >
        <input
          type="color"
          id={props.id}
          value={pickerValue()}
          onInput={(e) => onPickerInput(e.currentTarget.value)}
          onChange={(e) => onPickerCommit(e.currentTarget.value)}
        />
      </label>
      <div class="tweak-input">
        <input
          type="text"
          value={hex()}
          spellcheck={false}
          aria-label={`${props.tweak.label || props.tweak.name || props.tweak.key} hex value`}
          onInput={(e) => onHexInput(e.currentTarget.value)}
          onChange={(e) => onHexCommit(e.currentTarget.value)}
        />
      </div>
    </div>
  );
}

function SelectControl(props: ControlBaseProps) {
  // Phase 1 of the UnoCSS+Kobalte migration. Kobalte's ``Select``
  // primitive replaces the hand-rolled portal/scroll/escape logic that
  // lived here previously; visual styling stays on the existing
  // ``.tweak-select-*`` classes in ``styles.css`` so this is a pure
  // behavior swap.
  const options = () => props.tweak.options ?? [];
  return (
    <div class="tweak-select">
      <Select<string>
        value={props.initial || null}
        onChange={(v) => {
          // Discrete commit: ``onChange`` only fires on a real selection
          // change, matching the commit-on-release semantics shipped
          // for drag-style controls in 61dc11b.
          if (v != null) props.onCommit(v);
        }}
        options={options()}
        placeholder="—"
        gutter={4}
        sameWidth
        itemComponent={(p) => (
          <Select.Item item={p.item} class="tweak-select-option">
            <Select.ItemLabel>{p.item.rawValue}</Select.ItemLabel>
          </Select.Item>
        )}
      >
        <Select.Trigger class="tweak-select-trigger" id={props.id}>
          <Select.Value<string> class="tst-value">
            {(s) => s.selectedOption() || "—"}
          </Select.Value>
          <Select.Icon class="tst-caret i-lucide-chevron-down text-xs" />
        </Select.Trigger>
        <Select.Portal>
          <Select.Content class="tweak-select-menu is-open is-portal">
            <Select.Listbox />
          </Select.Content>
        </Select.Portal>
      </Select>
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  detail: string;
  class?: string;
}

function EmptyState(props: EmptyStateProps) {
  return (
    <div class={`empty-state${props.class ? ` ${props.class}` : ""}`}>
      <h2>{props.title}</h2>
      <p>{props.detail}</p>
    </div>
  );
}

// Mount on body via main.tsx; this file only exports App.
