## 1. Core Tweak Model

- [x] 1.1 Add internal tweak declaration/value dataclasses for key, group, label, type, default, constraints, mode, resolved value, and diagnostics under `folio.core.dsl.tweaks`.
- [x] 1.2 Implement a spec-scoped `TweakRegistry` that starts clean for each spec load and records declarations from imported modules.
- [x] 1.3 Implement duplicate-key detection and missing-default/type-specific declaration errors.
- [x] 1.4 Implement `TweakValue` wrappers with primitive coercion (`__str__`, `__float__`, `__int__`, `__bool__`) and a stable CSS-variable identifier (`--folio-tweak-<dotted-key-with-dashes>`).
- [x] 1.5 Add unit tests for registry isolation across repeated and sequential spec loads, duplicate keys, missing defaults, and primitive coercion behavior.

## 2. Public DSL API

- [x] 2.1 Add `folio.core.dsl.tweaks` with `group()`, `color()`, `size_pt()`, `size_mm()`, `opacity()`, `letter_spacing()`, `stroke_width()`, `choice()`, `preset()`, and `font_choice()` helpers. Do not add `image()` in this change.
- [x] 2.2 Re-export the `tweaks` namespace from `folio.core.dsl.__init__` and `folio.dsl` so users import `from folio.dsl import tweaks`.
- [x] 2.3 Type live-eligible `TextStyle` fields (`font_size_pt`, `letter_spacing`, `fill`, opacity-related fields) and live-eligible element-attribute fields as `float | TweakValue` (or `str | TweakValue` for color); store wrappers without primitive coercion at construction.
- [x] 2.4 Add DSL tests for colors in `fill`, numeric size values in `TextStyle`, group attribute access, duplicate keys, derived primitive expressions losing live metadata, and `TextStyle` storing `TweakValue` directly.

## 3. TOML Values and Diagnostics

- [x] 3.1 Resolve the persisted values file at `<spec_dir>/theme.toml`; do not accept `values_file=` overrides in this change.
- [x] 3.2 Implement TOML loading with `tomllib`, dotted-key/table mapping, and fallback to declaration defaults when the file is missing.
- [x] 3.3 Implement validation for supported value types, numeric ranges, choice options, invalid modes, and unknown persisted keys (warning, not error).
- [x] 3.4 Implement a deterministic writer for Folio-owned scalar/simple-array tweak values, grouped by TOML table in canonical sorted key order; document that comments are not preserved.
- [x] 3.5 Add tests for valid values, missing file defaults, invalid type, out-of-range values, unknown key warnings, and deterministic write output.

## 4. Spec Load and Build Integration

- [x] 4.1 Add a service-level helper that loads a spec, creates a tweak context, loads `theme.toml`, executes and renders the collection, and returns both `BuildResult` and a `TweakRegistry` snapshot.
- [x] 4.2 Update `folio validate` to use the helper and report invalid persisted tweak values as validation failures and unknown keys as warnings.
- [x] 4.3 Update `folio build` to use the helper and render artifacts from persisted tweak values; emit warnings for unknown persisted keys without failing the build.
- [x] 4.4 Ensure the last-build cache is refreshed from rendered SVGs that include the active tweak values.
- [x] 4.5 Add CLI tests for validate/build with valid values, invalid values, unknown key warnings, and specs without tweak declarations.

## 5. Renderer Mode Flag and Live-Eligible Formatter

- [x] 5.1 Add a render-mode flag (`build` or `playground`) to the renderer entry points used by `folio build`.
- [x] 5.2 Add a dedicated value formatter path for live-eligible attributes that bypasses `_mm` / `_pt` numeric normalization; in this change both modes emit concrete resolved values.
- [x] 5.3 Ensure geometry, page size, layout, image, and text-flow values remain rebuild-only and concrete in both modes.
- [x] 5.4 Add renderer tests proving build SVGs contain concrete values for tweak-backed attributes, no `var(--folio-tweak-...)` appears in any output, and the playground mode entry point is exercised end to end.

## 6. Starter, Docs, and Skill

- [ ] 6.1 Update the starter `theme.py` to declare a tweak group covering at least a brand color and a hero text size used by rendered pages; remove dual-homed token entries for those values.
- [ ] 6.2 Add a starter `theme.toml` with valid persisted values for the declared tweaks.
- [ ] 6.3 Update the starter `README.md` to explain `folio.dsl.tweaks` and `theme.toml`, with no playground references in this change.
- [ ] 6.4 Add docstrings and examples for all public tweak helpers.
- [ ] 6.5 Regenerate and commit the docs index so tweak helpers are searchable and examples pass.
- [ ] 6.6 Update the bundled Folio skill to describe tweak declarations, `theme.toml`, and the tokens-vs-tweaks rule, while keeping `folio check -> build -> rasterize -> reconcile` authoritative.

## 7. Verification

- [ ] 7.1 Run targeted unit tests for tweak model, TOML values, DSL integration, renderer modes, and CLI validate/build behavior.
- [ ] 7.2 Run starter-template generation/build tests and confirm generated projects include valid `theme.toml` and a buildable `theme.py`.
- [ ] 7.3 Run docs generation and example validation.
- [ ] 7.4 Run the full project test suite.
- [ ] 7.5 Run `openspec validate add-tweaks-model --strict` and fix any proposal/spec/task validation issues.
