# Capability: Tweaks Playground

## Purpose

Describe Folio's local browser playground for inspecting rendered pages and editing approved design-time tweak values without replacing production build outputs.

## Requirements

### Requirement: Playground command

Folio SHALL provide a local `folio dev` command that serves a browser playground for inspecting pages and editing declared tweak values.

#### Scenario: Starting the playground for a spec
- **WHEN** a user runs `folio dev <spec>` or `folio dev` inside a project directory
- **THEN** Folio resolves the spec using the same default spec rules as `folio build` and `folio validate`
- **AND** starts a loopback-only development server by default
- **AND** serves an HTML playground showing rendered page previews and the declared tweak controls

#### Scenario: Configurable host and port
- **WHEN** the user provides `--host` or `--port` to `folio dev`
- **THEN** Folio binds the development server to the requested host and port
- **AND** reports the served URL on stdout

#### Scenario: Open/no-open flag
- **WHEN** the user runs `folio dev --open`
- **THEN** Folio attempts to open the served URL in the user's default browser after the server is ready

#### Scenario: No-open default behavior
- **WHEN** the user runs `folio dev --no-open`, or runs `folio dev` in an environment where opening a browser is not supported
- **THEN** Folio does not attempt to open a browser
- **AND** still reports the served URL on stdout

#### Scenario: Playground with no tweaks
- **WHEN** the resolved spec renders successfully but declares no tweaks
- **THEN** the playground still shows page previews
- **AND** displays an empty-state message that no tweakable values were declared

#### Scenario: Playground startup render failure
- **WHEN** the resolved spec cannot be loaded, validated, or rendered
- **THEN** `folio dev` surfaces the error in the terminal or playground state
- **AND** does not silently serve stale page output as if it were current

### Requirement: Playground HTTP endpoints

Folio SHALL expose a minimal HTTP API for the playground UI.

#### Scenario: Playground shell endpoint
- **WHEN** an HTTP client requests `GET /`
- **THEN** the server returns the playground HTML shell

#### Scenario: State endpoint
- **WHEN** an HTTP client requests `GET /api/state`
- **THEN** the server returns rendered pages, tweak schema, resolved values, modes, warnings, and render diagnostics for the active spec

#### Scenario: Tweak update endpoint
- **WHEN** an HTTP client sends `PATCH /api/tweaks` with a value update for a declared tweak
- **THEN** the server validates the value against the tweak declaration
- **AND** on accept, writes the updated value to `<spec_dir>/theme.toml` using the deterministic writer
- **AND** returns either a live acknowledgement (for live-mode edits) or a rebuilt state (for rebuild-mode edits)

#### Scenario: Rejected edit
- **WHEN** an HTTP client sends `PATCH /api/tweaks` with a value that violates the tweak declaration
- **THEN** the server rejects the edit with a diagnostic naming the dotted key and reason
- **AND** does not write to `theme.toml`

### Requirement: Playground rendering mode

Folio SHALL render playground page previews in playground mode so live-safe attributes can be driven by CSS custom properties without affecting build outputs.

#### Scenario: Live-safe attribute set
- **WHEN** the playground renderer formats an attribute backed by a `live`-mode tweak
- **THEN** it may emit `var(--folio-tweak-<dotted-key-with-dashes>, <fallback>)` only for the following attributes: `fill`, `stroke`, `opacity`, `fill-opacity`, `stroke-opacity`, `font-size`, `letter-spacing`, and presentation `stroke-width`
- **AND** the fallback inside `var(...)` is the resolved primitive value at render time

#### Scenario: Non-live-safe attributes stay concrete
- **WHEN** the playground renderer formats an attribute outside the live-safe allow-list, or any attribute backed by a rebuild-mode tweak
- **THEN** the attribute value is emitted as a concrete resolved primitive

#### Scenario: Geometry attributes stay concrete
- **WHEN** the playground renderer formats geometry attributes (such as `x`, `y`, `width`, `height`, `r`, or page dimensions)
- **THEN** the values are concrete resolved primitives in both build and playground modes

#### Scenario: Build mode unaffected
- **WHEN** `folio build` invokes the renderer in build mode for a spec that declares live-mode tweaks
- **THEN** built SVG output contains only concrete resolved values
- **AND** does not contain `var(--folio-tweak-...)` references

### Requirement: Playground editing behavior

Folio SHALL apply playground edits according to each tweak's effective edit mode.

#### Scenario: Editing a live value
- **WHEN** the user changes a live-mode tweak control in the browser
- **THEN** the playground updates the corresponding CSS custom property on the preview container immediately
- **AND** sends the new value to `PATCH /api/tweaks` for persistence
- **AND** persistence may be debounced to reduce disk churn

#### Scenario: Editing a rebuild value
- **WHEN** the user changes a rebuild-mode tweak control in the browser
- **THEN** Folio persists the accepted value to `theme.toml`
- **AND** debounces a spec rerun
- **AND** replaces the affected page previews with the newly rendered output once the rebuild completes

#### Scenario: Live value used in a non-live context
- **WHEN** a live-mode tweak value is used in a context that the renderer cannot express as a CSS variable
- **THEN** the playground updates the persisted value immediately
- **AND** triggers a rebuild for that context to reflect the change

#### Scenario: Rejected edit visual feedback
- **WHEN** the user submits a value that violates the tweak declaration
- **THEN** the playground shows a validation error tied to the affected control
- **AND** does not modify `theme.toml`

#### Scenario: Persisted values survive restart
- **WHEN** a user edits tweak values, stops `folio dev`, and later runs `folio dev` or `folio build` again for the same spec
- **THEN** Folio loads the persisted values from `<spec_dir>/theme.toml`
- **AND** renders output using those values

### Requirement: Playground UI controls

Folio SHALL render appropriate playground controls for each declared tweak based on its declaration metadata.

#### Scenario: Color control
- **WHEN** a `color` tweak is rendered in the playground
- **THEN** the UI shows a color picker bound to the resolved value

#### Scenario: Numeric controls
- **WHEN** a numeric tweak (`size_pt`, `size_mm`, `opacity`, `letter_spacing`, `stroke_width`) declares `min` and `max`
- **THEN** the UI shows a range or numeric input bound to the resolved value and constrained to the declared range

#### Scenario: Choice and preset controls
- **WHEN** a `choice`, `preset`, or `font_choice` tweak is rendered
- **THEN** the UI shows a control listing the declared options
- **AND** the resolved value is the selected option

#### Scenario: Page selection
- **WHEN** the rendered document contains more than one page
- **THEN** the playground shows a page selector
- **AND** swapping pages does not lose pending edit state

### Requirement: Playground rendering isolation

Folio SHALL keep `folio dev` rendering separate from production build artifacts and reconcile cache state.

#### Scenario: Playground does not refresh last-build cache
- **WHEN** `folio dev` renders or rerenders page previews
- **THEN** Folio does not update the `folio build` last-build cache as a side effect
- **AND** reconcile continues to compare against explicit build cache state

#### Scenario: Production build resolves concrete values
- **WHEN** a user runs `folio build` for a spec that declares live-mode tweaks
- **THEN** built SVG output contains concrete resolved values for tweak-backed attributes
- **AND** does not depend on playground JavaScript or CSS custom properties

### Requirement: External editor races

Folio SHALL document and implement last-write-wins behavior when `theme.toml` is modified outside `folio dev`.

#### Scenario: External edit during playground session
- **WHEN** the user edits `theme.toml` in an external editor while `folio dev` is running
- **AND** the user then submits a tweak edit through the playground that the server accepts
- **THEN** the server writes the playground's view of values to `theme.toml`, overwriting the external edit

#### Scenario: Server rereads on each render
- **WHEN** `folio dev` performs a render or rerender
- **THEN** the server reloads `theme.toml` from disk before rendering
- **AND** uses the values currently on disk, falling back to declaration defaults for missing keys

### Requirement: Packaged playground frontend assets

Folio SHALL serve the `folio dev` browser UI from package-included compiled frontend assets rather than a monolithic embedded HTML string.

#### Scenario: Playground shell uses packaged asset
- **WHEN** an HTTP client requests `GET /`
- **THEN** the development server returns the compiled playground HTML asset bundled with the installed Folio package
- **AND** the response does not depend on Node, npm, or frontend source files being present on the user's machine

#### Scenario: Static playground assets are served safely
- **WHEN** the compiled playground HTML references JavaScript, CSS, or other static UI assets
- **THEN** the development server serves those assets from the packaged asset directory
- **AND** rejects path traversal, absolute paths, directories, and missing assets with safe HTTP error responses

#### Scenario: Existing JSON API remains available
- **WHEN** the packaged frontend requests `GET /api/state` or `PATCH /api/tweaks`
- **THEN** the server handles those requests using the existing playground JSON API contract
- **AND** the static asset serving routes do not shadow or change those API endpoints

### Requirement: Developer-only frontend build pipeline

Folio SHALL keep TypeScript/CSS frontend tooling as a repository and release-build concern, not as a runtime requirement for users of `folio dev`.

#### Scenario: Installed runtime has no Node requirement
- **WHEN** a user installs Folio from a wheel or sdist and runs `folio dev <spec>`
- **THEN** the playground starts and serves the bundled compiled UI using only Folio's Python runtime dependencies
- **AND** does not invoke `node`, `npm`, `npx`, or a TypeScript compiler at runtime

#### Scenario: Maintainer rebuild command
- **WHEN** a maintainer changes playground TypeScript or CSS source in the repository
- **THEN** the repository provides a documented command to regenerate the compiled playground assets
- **AND** the generated assets are written to the package-included asset location used by `folio dev`

#### Scenario: Stale or missing compiled assets are detected
- **WHEN** a maintainer runs the relevant package/build/test check with missing or stale compiled playground assets
- **THEN** the check fails with an actionable message naming the frontend rebuild command
- **AND** does not silently ship a playground shell that depends on source files outside the package

### Requirement: Document workspace playground layout

Folio SHALL present rendered playground pages in a scrollable document workspace rather than a single oversized preview slot.

#### Scenario: Continuous page canvas
- **WHEN** `GET /api/state` returns one or more rendered pages
- **THEN** the playground UI displays the pages as separate page cards in a continuous scrollable canvas
- **AND** each page card contains the rendered SVG for that page

#### Scenario: Page labels
- **WHEN** a rendered page is shown in the workspace
- **THEN** the UI shows a visible page label such as `Page 1` associated with that page card
- **AND** the label remains visible enough to orient the user while scrolling multi-page documents

#### Scenario: Empty or failed render state
- **WHEN** the server state contains no rendered pages because the document failed to load or render
- **THEN** the workspace shows a non-stale empty or error state
- **AND** does not present previous page SVGs as if they were current

### Requirement: Page navigation and zoom controls

Folio SHALL provide basic document navigation and zoom controls in the playground workspace.

#### Scenario: Current page selection
- **WHEN** the user clicks a page card or uses page navigation controls
- **THEN** the selected page is visually highlighted
- **AND** the navigation state reflects the selected page number

#### Scenario: Page navigation scrolls workspace
- **WHEN** the user selects a page through the navigation controls
- **THEN** the workspace scrolls the corresponding page card into view
- **AND** does not discard unsaved draft tweak values

#### Scenario: Fit width zoom
- **WHEN** the user selects `fit width` zoom
- **THEN** rendered pages scale to fit the available workspace width while preserving page aspect ratio

#### Scenario: Fit page zoom
- **WHEN** the user selects `fit page` zoom
- **THEN** the selected page scales so the whole page can be viewed within the workspace viewport when practical
- **AND** page aspect ratio is preserved

#### Scenario: Actual size zoom
- **WHEN** the user selects `100%` zoom
- **THEN** rendered pages use their natural SVG dimensions instead of fitting to the workspace width or height

### Requirement: Polished tweak inspector

Folio SHALL provide a polished inspector for declared tweak controls, diagnostics, and persistence status.

#### Scenario: Grouped controls
- **WHEN** the active spec declares tweaks from one or more tweak groups
- **THEN** the inspector groups controls by their tweak group name or equivalent dotted-key prefix
- **AND** preserves each control's label, type, bounds, options, and current resolved value

#### Scenario: Per-control validation feedback
- **WHEN** `PATCH /api/tweaks` rejects a submitted value for a declared tweak
- **THEN** the inspector displays a validation message attached to the affected control
- **AND** keeps the user's draft value visible until the user corrects or reloads it

#### Scenario: Global diagnostics
- **WHEN** `GET /api/state` returns warnings or render diagnostics not tied to one control
- **THEN** the UI displays those diagnostics in a visible global diagnostics area
- **AND** does not hide tweak controls that are otherwise valid

#### Scenario: Persistence status
- **WHEN** a tweak update is pending, accepted, rejected, or followed by a rerender
- **THEN** the inspector shows enough status for the user to understand whether the current value is saved, invalid, or still updating

#### Scenario: No tweaks empty state
- **WHEN** the active document renders successfully but declares no tweaks
- **THEN** the inspector shows a polished empty state explaining that no approved tweakable values were declared
- **AND** the document workspace remains usable for page inspection

### Requirement: Responsive playground UI

Folio SHALL adapt the playground workspace and inspector to narrow browser widths without losing core functionality.

#### Scenario: Desktop layout
- **WHEN** the viewport has enough horizontal space
- **THEN** the UI shows the document workspace and tweak inspector side by side
- **AND** the inspector remains usable while the page workspace scrolls

#### Scenario: Narrow layout
- **WHEN** the viewport is too narrow for a side-by-side layout
- **THEN** the UI stacks or otherwise reflows the workspace and inspector
- **AND** page navigation, zoom controls, diagnostics, and tweak controls remain reachable without horizontal scrolling of the whole page

### Requirement: Playground behavior preservation

Folio SHALL preserve the existing playground editing and production-output guarantees while replacing the frontend shell.

#### Scenario: Live CSS variable edits remain immediate
- **WHEN** the user changes a live-mode tweak in the polished UI
- **THEN** the UI updates the corresponding playground CSS custom property immediately
- **AND** still sends the accepted value through `PATCH /api/tweaks` for persistence

#### Scenario: Rebuild fallback remains available
- **WHEN** a tweak edit affects a rebuild-mode or derived/non-live context
- **THEN** the UI requests or consumes a rerendered server state after the debounced update
- **AND** replaces the affected page previews with the server-rendered output

#### Scenario: Production build remains concrete
- **WHEN** a user runs `folio build` after using the polished playground
- **THEN** the production artifacts contain concrete resolved tweak values
- **AND** do not depend on the playground JavaScript, CSS, or CSS custom properties

#### Scenario: Dev rendering remains cache-isolated
- **WHEN** `folio dev` renders or rerenders page previews through the polished UI
- **THEN** Folio does not update the `folio build` last-build cache as a side effect
