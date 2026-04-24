# src/folio/search/

## Responsibility

Provides two independent search capabilities for the Folio DSL:
- **Stock image search**: Queries third-party stock photo APIs (OpenVerse, Pexels, Pixabay) and returns typed `SearchResult` records.
- **SVG asset search**: Queries SVG/icon libraries (SVGL, Iconify, Simple Icons) with live URL verification and ranked scoring, returning `SvgSearchResponse`.

## Design

### Stock Image Search (`providers.py`)

- `Provider = Literal["openverse", "pexels", "pixabay"]` — closed union type for the supported providers.
- `SearchResult` — frozen dataclass with immutable fields: id, provider, description, url, thumbnail, width, height, license, creator, source.
- `_FETCHERS` registry maps each provider string to its private fetcher function.
- **OpenVerse**: Public API, no auth required. Fetches `https://api.openverse.org/v1/images/`.
- **Pexels**: Requires `PEXELS_API_KEY` env var; raises `RuntimeError` if absent.
- **Pixabay**: Requires `PIXABAY_API_KEY` env var; raises `RuntimeError` if absent.
- `fetch_stock()` — single-provider search via dispatcher.
- `fetch_stock_multi()` — multi-provider search with graceful degradation: collects results from successful providers, raises only when every provider fails.

All HTTP uses stdlib `urllib` only (no external dependencies).

### SVG Asset Search (`svg.py`)

- `SvgSearchError(Exception)` — raised on invalid input or when all providers fail.
- `SvgSearchResult(frozen, slots=True)` — immutable result record. Fields: source, title, svg_url, subtitle, identifier, website, wordmark_url, verified.
- `SvgSearchResponse(frozen)` — aggregates a query, its ranked+verified results, and any warnings.
- `_normalize_sources()` — validates and deduplicates source names against `SUPPORTED_SVG_SOURCES`. Raises `SvgSearchError` on unknown source.
- `_result_score()` — scoring tuple `(exact_match, contains_match, source_priority, title_key)` for deterministic sort ordering. Exact title match ranks above substring; SVGL > simple-icons > iconify; iconify prefixes are further scored by `PREFERRED_ICONIFY_PREFIXES` order.
- `_probe_svg_url()` — performs an HTTP HEAD/partial-GET and validates either `Content-Type: image/svg+xml` or that the response body starts with `<svg` or `<?xml`.
- `_verify_results()` — iterates results in rank order, probes unverified ones, sets `verified=True` on success.
- `_search_svgl()` — queries `https://api.svgl.app?search=...`, maps `route.light`/`route.dark` to `svg_url`, returns up to `limit` results.
- `_search_simple_icons()` — generates slug candidates (raw, compact alphanumeric, dashed kebab), probes `https://cdn.simpleicons.org/{slug}` per candidate, auto-verifies found logos.
- `_search_iconify()` — queries `https://api.iconify.design/search?query=...&limit=...`, sorts icons by `PREFERRED_ICONIFY_PREFIXES` priority, builds `SvgSearchResult` with `identifier=prefix:name` for downstream use.
- `search_svg_assets()` — main entry point: validates input, dispatches to per-source searchers in `normalized_sources` order, deduplicates by `(source, svg_url)`, sorts by `_result_score()`, verifies top N, returns `SvgSearchResponse`.

## Flow

**Stock search:**
```
fetch_stock(query, provider=...)
  → _FETCHERS[provider](query)
    → _http_get_json(url)           # urllib + json.loads
    → provider-specific mapper     # SearchResult list
```

```
fetch_stock_multi(query, providers=[...])
  → for prov in providers:
      try: _FETCHERS[prov](query)
      except: collect error
  → raise RuntimeError if all failed
  → return combined SearchResult list
```

**SVG search:**
```
search_svg_assets(query, limit=8, sources=None)
  → validate (query non-empty, limit >= 1)
  → _normalize_sources(sources)    # default: svgl, simple-icons, iconify
  → for source in normalized_sources:
      _search_svgl | _search_simple_icons | _search_iconify
  → _dedupe_results(by (source, svg_url))
  → sorted(_result_score)
  → _verify_results(limit=limit)   # probe + set verified=True
  → SvgSearchResponse
```

## Integration

- Public API re-exported from `__init__.py`: `PROVIDERS`, `Provider`, `SearchResult`, `fetch_stock`, `fetch_stock_multi`.
- `search_svg_assets` is not re-exported in `__init__.py` (direct import from `folio.search.svg`).
- Consumed by: CLI search command (`folio/commands/search/`), DSL SVG/image reference resolution, reconcile engine for external asset validation.
- Depends on: stdlib `urllib`, `json`, `dataclasses`. No external HTTP libraries.
