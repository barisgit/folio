## ADDED Requirements

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
