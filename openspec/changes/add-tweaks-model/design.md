## Context

Folio loads Python specs through `src/folio/core/dsl/loader.py`, materializes immutable `Document` / `Page` / `Element` dataclasses, and renders page SVGs through `src/folio/core/render/pipeline.py`. CLI commands are thin Typer adapters under `src/folio/cli/`; build execution already separates spec loading, rendering, export planning, cache writing, and rasterization.

This change isolates the tweak data model and pipeline integration from any browser story. The companion change `add-tweaks-playground` adds `folio dev` on top of this foundation.

Important constraints:

- `build.py` is the default spec entrypoint; sibling modules (e.g. `theme.py`) are importable during spec execution and that flow must keep working.
- The renderer currently normalizes `_mm` / `_pt` attributes through numeric conversion; CSS variables must not be routed through that path. This change does not yet emit CSS variables, but the renderer must gain a render-mode flag so the playground change can plug in cleanly.
- Build/export artifacts must remain deterministic static outputs for downstream SVG/PDF/PNG/IDML workflows.
- Reconcile depends on stable SVG element ids and concrete attribute values; build outputs in this change remain fully concrete.
- Python 3.11 includes `tomllib` for reading TOML but no standard TOML writer; this change ships a small purpose-built writer.

## Goals / Non-Goals

**Goals:**

- Add a typed tweak declaration API under `folio.dsl.tweaks` (re-exported from `folio.core.dsl.tweaks`).
- Let specs keep schema in Python while persisted user-selected values live in `<spec_dir>/theme.toml`.
- Make tweak values usable in normal Folio specs as colors, numbers, strings, or choices via `TweakValue` wrappers.
- Preserve `TweakValue` (no primitive coercion) on live-eligible style/element-attribute fields, so a future playground change can emit `var(--folio-tweak-...)` without re-touching `TextStyle` and friends.
- Make `folio validate` and `folio build` authoritative: load persisted values, validate them, render artifacts with concrete resolved values, refresh the last-build cache.
- Move tweakable brand values in the starter from `tokens` to `tweaks` (single source of truth); update docs, examples, and skill.

**Non-Goals:**

- Any browser playground, `folio dev` command, or HTTP server.
- Live CSS-variable injection at the SVG attribute boundary (renderer gains the mode flag, but only build mode is wired up here).
- `--tweak key=value` CLI overrides or one-shot ad-hoc tweak experiments.
- `image()` tweak helper; deferred until asset-resolution semantics are settled.
- Comment-preserving TOML round-tripping; `theme.toml` is a Folio-managed values file in this change.
- Multi-file, preset, or cross-project value sharing; `<spec_dir>/theme.toml` is the only persisted source.

## Decisions

1. **Schema in Python, values in TOML.**

   Specs declare tweak schema through Python helpers; values live in `<spec_dir>/theme.toml`. Authoring shape:

   ```python
   from folio.dsl import TextStyle, tweaks

   theme = tweaks.group(
       "theme",
       primary=tweaks.color(default="#d9a64b", label="Primary brand"),
       accent=tweaks.color(default="#ff5a3c", label="Accent"),
       hero_size_pt=tweaks.size_pt(default=58, label="Hero size", min=32, max=76),
       card_gap_mm=tweaks.size_mm(default=8, label="Card gap", min=4, max=16),
   )

   HERO = TextStyle(font_size_pt=theme.hero_size_pt, fill=theme.primary)
   ```

   Matching values file:

   ```toml
   [theme]
   primary = "#d9a64b"
   accent = "#ff5a3c"
   hero_size_pt = 58
   card_gap_mm = 8
   ```

   Rationale: Python remains the source of truth for what is tweakable, with labels, defaults, ranges, and type safety. TOML is reviewable, agent-friendly, and safe for programmatic writes without mutating Python source. Rejected: paste-back workflows (latency, drift), YAML/JSON-only schema (duplicates the DSL), browser editing of `theme.py` (out of scope for this change and the next).

2. **Spec-scoped `TweakRegistry`.**

   A context-local `TweakRegistry` is created by the spec load/render service, populated as `folio.dsl.tweaks` helpers run during spec execution, then snapshotted alongside the `BuildResult`. Imported modules such as `theme.py` register declarations into the active context.

   Rejected: static AST extraction (real specs branch and import), process-global registry (stale state across CLI invocations and tests).

   Implementation implication: introduce a single service helper used by `validate` and `build`. Existing call sites that open-code `load_dsl_module()` + `collection_from_module()` migrate to the helper when they need tweak metadata.

3. **`TweakValue` wrappers preserve metadata on live-eligible fields.**

   Tweak helpers return `TweakValue` objects with the resolved primitive value, declaration metadata, and a stable CSS-variable identifier. They are primitive-coercible (`__str__`, `__float__`, `__int__`, `__bool__`) for arbitrary Python use, but `TextStyle` and live-eligible element-attribute fields are typed `float | TweakValue` (or `str | TweakValue` for color) and store the wrapper without coercion.

   Rationale: in this change, the renderer always resolves `TweakValue` to a concrete primitive at the build attribute boundary; in `add-tweaks-playground`, the same fields can carry the wrapper through to a CSS-variable-emitting renderer mode. Without this, live `font-size` would silently degrade to rebuild because `TextStyle.font_size_pt` would be a plain `float`.

   Limitation: derived expressions (`float(theme.x) + 4`) lose metadata and are rebuild-only. Document this and cover it with a test.

4. **Per-class default edit modes (locked in spec).**

   Each tweak class declares a `default_mode` of `live` or `rebuild`. Authors do not specify mode unless a class permits override.

   - `color`: live
   - `opacity`: live
   - `letter_spacing`: live
   - `size_pt`: live (direct text/font-size attribute use); rebuild for derived/layout uses
   - `size_mm`: rebuild
   - `stroke_width`: live when used as SVG presentation `stroke-width`, otherwise rebuild
   - `choice`: rebuild
   - `preset`: rebuild
   - `font_choice`: rebuild

   Rationale: live-vs-rebuild is mostly a property of the value class and its safe rendering contexts. Rejected: forcing every author to pass `mode=`; encourages unsafe live declarations for layout-affecting values.

   This table lives in `specs/tweaks/spec.md` (not just here) so it is an enforceable contract.

5. **Renderer gains a build-vs-playground mode flag.**

   Build/export rendering emits concrete resolved values for all attributes. A `playground` mode is reserved at the renderer interface; in this change it produces the same output as build mode (no CSS variables yet), so the integration surface is locked but the playground change is not blocked.

   Implementation implication: renderer value formatting becomes mode-aware at the attribute boundary. Geometry attributes (`x`, `y`, `width`, `height`, `r`, page dimensions) remain concrete in both modes and stay outside the `_mm`/`_pt` numeric path for any future CSS-variable use.

6. **Narrow deterministic TOML writer.**

   Read with `tomllib`. Write with a small purpose-built writer that emits strings, ints, floats, booleans, and simple arrays grouped by TOML table in canonical sorted key order. `theme.toml` is declared a Folio-managed values file: comments and user formatting are not preserved on write.

   Rejected: a third-party TOML editor library now (extra dependency surface for a value file we own).

7. **Diagnostics are part of the contract.**

   Invalid persisted values are errors in `folio validate` and `folio build`. Unknown persisted keys are warnings (often stale values after a tweak rename); they do not fail builds. Diagnostics include the values file path, dotted key, expected type/range/options, and the offending value.

8. **Starter moves tweakable brand values to `tweaks`; no dual-home.**

   The starter `theme.py` keeps non-tweakable named colors in `tokens.extend(...)` and replaces the brand color and hero text size constants with tweak declarations. The generated `theme.toml` ships valid persisted values. Rationale: one source of truth per value avoids agent confusion and drift.

9. **`folio docs` indexes public tweak helpers; bundled skill teaches the model.**

   `folio docs generate` adds tweak helpers to the index, examples validate without requiring a project `theme.toml`, and the bundled `SKILL.md` instructs agents to declare tweakables in Python and edit values in `theme.toml` rather than hand-editing built SVGs.

## Risks / Trade-offs

- **Risk: `TweakValue` behaves surprisingly in arbitrary Python.** → Mitigation: keep wrappers primitive-coercible, document derived-expression limits, test common `TextStyle`/primitive paths and arithmetic coercion.
- **Risk: invalid TOML blocks normal builds.** → Mitigation: precise diagnostics with file path, dotted key, expected type/range/options, and current invalid value.
- **Risk: deterministic write drops user comments in `theme.toml`.** → Mitigation: declare the file Folio-managed; keep schema/labels/docs in Python where comments belong.
- **Risk: renderer mode flag goes unused and rots before the playground change lands.** → Mitigation: cover both modes by tests now (playground mode currently equals build mode but the integration point and formatter dispatch must be exercised).
- **Risk: starter migration breaks projects that import `tokens.AMBER` etc.** → Mitigation: starter is a template; existing scaffolded projects are unaffected. Migration note in the bundled skill.
- **Risk: `_mm`/`_pt` numeric normalization rejects future CSS-variable values.** → Mitigation: route live-eligible attributes through a separate formatter path now, even though only concrete values flow through it in this change.

## Migration Plan

1. Add tweak model/registry/value-resolution internals and unit tests independent of rendering.
2. Add `folio.core.dsl.tweaks` and re-export through `folio.dsl.tweaks`.
3. Add TOML read/write with validation diagnostics.
4. Make `TextStyle` and live-eligible element-attribute fields accept `float | TweakValue` (or `str | TweakValue` for color) without coercing at construction.
5. Add the renderer build/playground mode flag with mode-aware attribute formatting; keep both modes concrete-only in this change.
6. Add the service-level spec load/render helper that returns `BuildResult` plus a `TweakRegistry` snapshot.
7. Update `folio validate` and `folio build` to use the helper, fail on invalid persisted values, warn on unknown keys, and refresh the last-build cache.
8. Update the starter template (`theme.py` + `theme.toml`), `folio docs` index, docs examples, README, and bundled skill.
9. Run targeted tests, full project tests, and `openspec validate add-tweaks-model --strict`.

Rollback: remove `folio.dsl.tweaks` exports, revert `validate`/`build` helper integration, revert starter/docs/skill edits. Specs without tweak declarations are unaffected because the default render path stays concrete.
