# Capability: Asset Search

## Purpose

Describe Folio's built-in search workflows for stock images and public SVG/logo assets.

## Requirements

### Requirement: Stock image search command
Folio SHALL provide a CLI for searching stock images from supported providers.

#### Scenario: Default provider
- **WHEN** a user runs `folio search stock <query>` without `--provider`
- **THEN** Folio searches `openverse` by default

#### Scenario: Explicit provider selection
- **WHEN** a user repeats `--provider` with one or more supported providers from `openverse`, `pexels`, and `pixabay`
- **THEN** Folio searches the requested providers in the provided set
- **AND** accepts `all` as shorthand for all supported stock providers

#### Scenario: Invalid provider selection
- **WHEN** a user requests an unknown stock provider
- **THEN** Folio rejects the command with a clear error listing the valid providers

#### Scenario: Result output modes
- **WHEN** stock search succeeds
- **THEN** Folio can render either a human-readable table or machine-readable JSON
- **AND** each result includes id, provider, description, URL, thumbnail, width, height, and any provider metadata that is available

#### Scenario: Empty result set
- **WHEN** the selected provider search returns no matches
- **THEN** Folio reports that no results were found without treating it as a request failure

### Requirement: Stock provider behavior
Folio SHALL support provider-specific authentication while degrading gracefully for multi-provider searches.

#### Scenario: Provider API key requirements
- **WHEN** a user searches Pexels or Pixabay without the required API key environment variable
- **THEN** Folio reports a provider error instead of attempting an unauthenticated request

#### Scenario: Multi-provider graceful degradation
- **WHEN** a stock search spans multiple providers and one provider fails
- **THEN** Folio still returns combined results from successful providers
- **AND** only fails the overall search when every selected provider fails

### Requirement: SVG asset search command
Folio SHALL provide a CLI for searching public SVG sources for logos and icons.

#### Scenario: Source selection
- **WHEN** a user runs `folio search svg <query>`
- **THEN** Folio searches the default SVG sources
- **AND** a user may restrict the search to `svgl`, `simple-icons`, and/or `iconify` by repeating `--source`

#### Scenario: Invalid SVG source
- **WHEN** a user requests an unsupported SVG source
- **THEN** Folio rejects the request with a clear validation error

#### Scenario: SVG result output modes
- **WHEN** SVG search succeeds
- **THEN** Folio can render either a human-readable table or machine-readable JSON
- **AND** each result includes the source, title, SVG URL, verification state, and any available context such as identifier, subtitle, website, or wordmark URL

### Requirement: Ranked and verified SVG results
Folio SHALL rank and verify SVG results before returning them.

#### Scenario: Ranking across sources
- **WHEN** Folio aggregates SVG matches from multiple sources
- **THEN** it deduplicates them
- **AND** ranks them using exact/contains matching plus source preference that favors SVGL, then Simple Icons, then Iconify

#### Scenario: Verification of SVG URLs
- **WHEN** Folio prepares the final SVG result set
- **THEN** it verifies candidate SVG URLs before returning them as results

#### Scenario: Partial source failures
- **WHEN** one SVG source fails but others return results
- **THEN** Folio returns the verified results it has
- **AND** surfaces source-specific warnings alongside the successful response
