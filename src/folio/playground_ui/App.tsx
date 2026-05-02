// Folio playground UI rendered with Solid.
//
// Component shape mirrors the prior vanilla-DOM implementation in
// ``main.ts`` (preserved in git history). Every CSS class name and ARIA
// attribute is carried over so the existing ``styles.css`` works
// unchanged. State lives in the store from ``state.ts``; this file is
// pure rendering.

import {
  For,
  Show,
  createEffect,
  createMemo,
  createSignal,
  onCleanup,
  onMount,
} from "solid-js";
import { Portal } from "solid-js/web";

import type { PlaygroundTweak } from "./api.generated";
import {
  type PlaygroundStore,
  isChoiceKind,
  isHexColor,
  isNumericKind,
  liveCssValue,
  normalizeInputValue,
  pad2,
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

  const specPathDisplay = createMemo(() => {
    const path = store.state()?.specPath || "";
    if (!path) return { short: "—", full: "" };
    const segments = path.split("/").filter(Boolean);
    const short = segments.length > 2 ? `…/${segments.slice(-2).join("/")}` : path;
    return { short, full: path };
  });

  return (
    <main id="folio-playground">
      <Topbar store={store} specPath={specPathDisplay} />

      <Workspace store={store} />

      <aside class="panel" aria-label="Tweak controls">
        <div class="panel-header">
          <div>
            <p class="eyebrow">APPROVED VALUES</p>
            <h2>Tweaks</h2>
          </div>
          <div class="panel-header-actions">
            <button
              type="button"
              class="reset-btn reset-btn-all"
              onClick={() => {
                if (!divergedTotal()) return;
                if (
                  typeof window !== "undefined" &&
                  !window.confirm(
                    `Reset all ${divergedTotal()} edited tweak(s) to spec defaults?`,
                  )
                ) {
                  return;
                }
                void store.resetTweaks({ scope: "all" });
              }}
              disabled={!divergedTotal()}
              title={
                divergedTotal()
                  ? `Reset all ${divergedTotal()} edited tweak(s)`
                  : "No tweaks edited from defaults"
              }
            >
              Reset all
              <Show when={divergedTotal() > 0}>
                <span class="reset-btn-count">{divergedTotal()}</span>
              </Show>
            </button>
            <span class="panel-count" aria-live="polite">
              {store.state()?.tweaks.length ?? 0}
            </span>
          </div>
        </div>

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
                      <button
                        type="button"
                        class="reset-btn reset-btn-group"
                        onClick={() => {
                          if (!divergedInGroup()) return;
                          void store.resetTweaks({
                            scope: "group",
                            group: groupName,
                          });
                        }}
                        disabled={!divergedInGroup()}
                        title={
                          divergedInGroup()
                            ? `Reset ${divergedInGroup()} tweak(s) in ${groupName}`
                            : "No tweaks edited from defaults"
                        }
                      >
                        Reset group
                      </button>
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

interface TopbarProps {
  store: PlaygroundStore;
  specPath: () => { short: string; full: string };
}

function Topbar(props: TopbarProps) {
  return (
    <header class="topbar" aria-label="Playground header">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6">
            <path d="M5 4h10l4 4v12H5z" />
            <path d="M15 4v4h4" />
            <path d="M9 12h6M9 16h6" />
          </svg>
        </span>
        <div class="brand-text">
          <span class="brand-eyebrow">FOLIO · DEV</span>
          <span class="brand-title">Playground</span>
        </div>
      </div>

      <div class="topbar-meta" aria-label="Active document">
        <span class="meta-eyebrow">SPEC</span>
        <span class="meta-value" title={props.specPath().full}>
          {props.specPath().short}
        </span>
      </div>

      <div class="topbar-status" aria-label="Render status">
        <span class="status-dot" data-state={props.store.globalStatus().state} aria-hidden="true" />
        <span class="status-text" role="status" aria-live="polite">
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
      <div class="workspace-toolbar" aria-label="Document controls">
        <div class="page-nav" aria-label="Page navigation">
          <button
            type="button"
            class="ghost-button"
            aria-label="Previous page"
            title="Previous page (PgUp)"
            disabled={pageCount() === 0 || props.store.selectedPageIndex() <= 0}
            onClick={() => selectPage(props.store.selectedPageIndex() - 1)}
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <PageSelector store={props.store} onSelect={(i) => selectPage(i, true)} />
          <button
            type="button"
            class="ghost-button"
            aria-label="Next page"
            title="Next page (PgDn)"
            disabled={pageCount() === 0 || props.store.selectedPageIndex() >= pageCount() - 1}
            onClick={() => selectPage(props.store.selectedPageIndex() + 1)}
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 6l6 6-6 6" />
            </svg>
          </button>
        </div>

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

interface PageSelectorProps {
  store: PlaygroundStore;
  onSelect: (index: number) => void;
}

function PageSelector(props: PageSelectorProps) {
  const [open, setOpen] = createSignal(false);
  let hostEl: HTMLDivElement | undefined;
  let triggerEl: HTMLButtonElement | undefined;

  function close(): void {
    setOpen(false);
  }

  function onDocumentClick(event: MouseEvent): void {
    if (hostEl && !hostEl.contains(event.target as Node)) close();
  }

  function onDocumentKeydown(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      triggerEl?.focus();
    }
  }

  createEffect(() => {
    if (open()) {
      document.addEventListener("click", onDocumentClick, true);
      document.addEventListener("keydown", onDocumentKeydown);
    } else {
      document.removeEventListener("click", onDocumentClick, true);
      document.removeEventListener("keydown", onDocumentKeydown);
    }
  });

  onCleanup(() => {
    document.removeEventListener("click", onDocumentClick, true);
    document.removeEventListener("keydown", onDocumentKeydown);
  });

  const pages = () => props.store.state()?.pages || [];
  const total = () => pages().length;
  const current = () => pages()[props.store.selectedPageIndex()];

  return (
    <div ref={hostEl} class="page-selector">
      <button
        ref={triggerEl}
        type="button"
        class="page-selector-trigger"
        disabled={total() === 0}
        aria-haspopup="listbox"
        aria-expanded={open()}
        onClick={() => setOpen(!open())}
      >
        <span class="pst-index">
          {total() ? pad2(props.store.selectedPageIndex() + 1) : "—"}
        </span>
        <span class="pst-sep"> / </span>
        <span class="pst-total">{total() ? pad2(total()) : ""}</span>
        <Show when={current()}>
          {(page) => (
            <span class="pst-name" title={page().filename}>
              {page().filename}
            </span>
          )}
        </Show>
        <span class="pst-caret">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.4">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </span>
      </button>
      <div
        class="page-selector-menu"
        classList={{ "is-open": open() }}
        role="listbox"
      >
        <For each={pages()}>
          {(page, index) => (
            <button
              type="button"
              class="page-selector-option"
              role="option"
              aria-selected={index() === props.store.selectedPageIndex()}
              data-index={index()}
              onClick={() => {
                props.onSelect(index());
                close();
              }}
            >
              <span class="pso-index">{pad2(page.pageNumber)}</span>
              <span class="pso-name">{page.filename}</span>
            </button>
          )}
        </For>
      </div>
    </div>
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
        <label for={inputId()}>
          {props.tweak.label || props.tweak.name || props.tweak.key}
        </label>
        <div class="tweak-head-right">
        <div class="tweak-meta">
          <span class="tm-key">{props.tweak.key}</span>
          <span class="tm-sep">·</span>
          <span class="tm-kind">{props.tweak.kind}</span>
          <span class="tm-sep">·</span>
          <span class="tm-mode" data-mode={props.tweak.mode}>{props.tweak.mode}</span>
        </div>
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
            <svg
              width="12"
              height="12"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M3 8a5 5 0 1 0 1.6-3.65" />
              <path d="M2.5 2.5v3h3" />
            </svg>
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
  const [open, setOpen] = createSignal(false);
  const [value, setValue] = createSignal(props.initial);
  // Trigger viewport rect so the menu can be portaled to <body> and
  // escape ``overflow: auto`` clipping on the surrounding tweak panel.
  const [rect, setRect] = createSignal<{ top: number; left: number; width: number } | null>(null);
  let triggerEl: HTMLButtonElement | undefined;
  let menuEl: HTMLDivElement | undefined;

  function close(): void {
    setOpen(false);
  }

  function refreshRect(): void {
    if (!triggerEl) return;
    const r = triggerEl.getBoundingClientRect();
    setRect({ top: r.bottom + 4, left: r.left, width: r.width });
  }

  function onDocClick(event: MouseEvent): void {
    const target = event.target as Node;
    if (triggerEl?.contains(target)) return;
    if (menuEl?.contains(target)) return;
    close();
  }

  function onDocKey(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      triggerEl?.focus();
    }
  }

  createEffect(() => {
    if (open()) {
      refreshRect();
      document.addEventListener("click", onDocClick, true);
      document.addEventListener("keydown", onDocKey);
      // Close on scroll/resize: the menu is fixed-positioned, so any
      // viewport change would unanchor it. Scroll listener is capture
      // so it fires for the inner ``.tweak-panel`` scroll container too.
      window.addEventListener("scroll", close, true);
      window.addEventListener("resize", close);
    } else {
      document.removeEventListener("click", onDocClick, true);
      document.removeEventListener("keydown", onDocKey);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    }
  });

  onCleanup(() => {
    document.removeEventListener("click", onDocClick, true);
    document.removeEventListener("keydown", onDocKey);
    window.removeEventListener("scroll", close, true);
    window.removeEventListener("resize", close);
  });

  function pick(option: string): void {
    setValue(option);
    // Discrete commit: the user clicked an option, so PATCH right away.
    props.onCommit(option);
    close();
  }

  return (
    <div class="tweak-select">
      <button
        ref={triggerEl}
        type="button"
        class="tweak-select-trigger"
        id={props.id}
        aria-haspopup="listbox"
        aria-expanded={open()}
        onClick={() => setOpen(!open())}
      >
        <span class="tst-value">{value() || "—"}</span>
        <span class="tst-caret">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.4">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </span>
      </button>
      <Show when={open() && rect()}>
        <Portal>
          <div
            ref={menuEl}
            class="tweak-select-menu is-open is-portal"
            role="listbox"
            style={{
              position: "fixed",
              top: `${rect()!.top}px`,
              left: `${rect()!.left}px`,
              width: `${rect()!.width}px`,
            }}
          >
            <For each={props.tweak.options || []}>
              {(option) => (
                <button
                  type="button"
                  class="tweak-select-option"
                  role="option"
                  aria-selected={option === value()}
                  onClick={() => pick(option)}
                >
                  {option}
                </button>
              )}
            </For>
          </div>
        </Portal>
      </Show>
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
