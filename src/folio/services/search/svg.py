from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_SVG_RESULT_LIMIT = 8
REQUEST_TIMEOUT_SECONDS = 20
SVG_SEARCH_USER_AGENT = "Mozilla/5.0 folio-svg-search"
SUPPORTED_SVG_SOURCES = ("svgl", "simple-icons", "iconify")
PREFERRED_ICONIFY_PREFIXES = (
    "logos",
    "simple-icons",
    "lucide",
    "tabler",
    "heroicons",
    "ph",
    "mdi",
    "carbon",
    "material-symbols",
)


class SvgSearchError(Exception):
    """Raised when SVG search input or provider access is invalid."""


@dataclass(frozen=True, slots=True)
class SvgSearchResult:
    source: str
    title: str
    svg_url: str
    subtitle: str | None = None
    identifier: str | None = None
    website: str | None = None
    wordmark_url: str | None = None
    verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SvgSearchResponse:
    query: str
    results: list[SvgSearchResult]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [result.to_dict() for result in self.results],
            "warnings": list(self.warnings),
        }


def _request(url: str, *, accept: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": SVG_SEARCH_USER_AGENT,
            "Accept": accept,
        },
    )


def _fetch_json(url: str) -> Any:
    with urllib.request.urlopen(
        _request(url, accept="application/json"),
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def _is_no_results_error(exc: Exception) -> bool:
    return isinstance(exc, urllib.error.HTTPError) and exc.code == 404


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _simple_icon_slug_candidates(query: str) -> list[str]:
    variants: list[str] = []
    raw = query.strip()
    compact = _normalize_text(raw)
    dashed = re.sub(r"[^a-z0-9]+", "-", raw.casefold()).strip("-")

    for candidate in (raw.casefold(), compact, dashed):
        normalized = candidate.strip()
        if normalized and normalized not in variants:
            variants.append(normalized)

    return variants


def _result_score(result: SvgSearchResult, *, query: str) -> tuple[int, int, int, str]:
    normalized_query = _normalize_text(query)
    fields = [result.title, result.identifier or "", result.website or "", result.subtitle or ""]
    normalized_fields = [_normalize_text(field) for field in fields if field]

    exact_match = 0 if any(field == normalized_query for field in normalized_fields[:2]) else 1
    contains_match = (
        0
        if any(normalized_query and normalized_query in field for field in normalized_fields)
        else 1
    )
    source_priority = {"svgl": 0, "simple-icons": 1, "iconify": 2}.get(result.source, 99)

    iconify_priority = 0
    if result.source == "iconify" and result.identifier:
        prefix = result.identifier.split(":", maxsplit=1)[0]
        try:
            iconify_priority = PREFERRED_ICONIFY_PREFIXES.index(prefix)
        except ValueError:
            iconify_priority = len(PREFERRED_ICONIFY_PREFIXES)

    title_key = f"{iconify_priority}:{result.title.casefold()}"
    return (exact_match, contains_match, source_priority, title_key)


def _dedupe_results(results: Iterable[SvgSearchResult]) -> list[SvgSearchResult]:
    deduped: list[SvgSearchResult] = []
    seen: set[tuple[str, str]] = set()

    for result in results:
        key = (result.source, result.svg_url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)

    return deduped


def _probe_svg_url(url: str) -> bool:
    try:
        with urllib.request.urlopen(
            _request(url, accept="image/svg+xml,text/plain;q=0.9,*/*;q=0.1"),
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            content_type = response.headers.get_content_type()
            if content_type == "image/svg+xml":
                return True
            snippet = response.read(512).decode("utf-8", errors="ignore").lstrip()
            return snippet.startswith("<svg") or snippet.startswith("<?xml")
    except Exception:
        return False


def _verify_results(results: Iterable[SvgSearchResult], *, limit: int) -> list[SvgSearchResult]:
    verified: list[SvgSearchResult] = []
    for result in results:
        if len(verified) >= limit:
            break
        if result.verified or _probe_svg_url(result.svg_url):
            verified.append(
                SvgSearchResult(
                    source=result.source,
                    title=result.title,
                    svg_url=result.svg_url,
                    subtitle=result.subtitle,
                    identifier=result.identifier,
                    website=result.website,
                    wordmark_url=result.wordmark_url,
                    verified=True,
                )
            )
    return verified


def _search_svgl(query: str, *, limit: int) -> tuple[list[SvgSearchResult], str | None]:
    url = f"https://api.svgl.app?search={urllib.parse.quote(query)}"
    try:
        data = _fetch_json(url)
    except Exception as exc:
        if _is_no_results_error(exc):
            return [], None
        return [], f"svgl lookup failed: {exc}"

    results: list[SvgSearchResult] = []
    for item in data[:limit]:
        route = item.get("route")
        svg_url = route.get("light") or route.get("dark") if isinstance(route, dict) else route
        if not isinstance(svg_url, str) or not svg_url:
            continue
        title = str(item.get("title") or svg_url.rsplit("/", maxsplit=1)[-1])
        results.append(
            SvgSearchResult(
                source="svgl",
                title=title,
                svg_url=svg_url,
                subtitle=str(item.get("category")) if item.get("category") else None,
                website=str(item.get("url")) if item.get("url") else None,
                wordmark_url=str(item.get("wordmark")) if item.get("wordmark") else None,
            )
        )
    return results, None


def _iconify_rank(icon_name: str) -> tuple[int, str]:
    prefix = icon_name.split(":", maxsplit=1)[0]
    try:
        priority = PREFERRED_ICONIFY_PREFIXES.index(prefix)
    except ValueError:
        priority = len(PREFERRED_ICONIFY_PREFIXES)
    return (priority, icon_name)


def _search_iconify(query: str, *, limit: int) -> tuple[list[SvgSearchResult], str | None]:
    expanded_limit = max(limit * 3, limit)
    url = (
        "https://api.iconify.design/search?"
        f"query={urllib.parse.quote(query)}&limit={expanded_limit}"
    )
    try:
        data = _fetch_json(url)
    except Exception as exc:
        if _is_no_results_error(exc):
            return [], None
        return [], f"iconify lookup failed: {exc}"

    collections = data.get("collections", {})
    icons = sorted(data.get("icons", []), key=_iconify_rank)

    results: list[SvgSearchResult] = []
    for icon in icons:
        if not isinstance(icon, str) or ":" not in icon:
            continue
        prefix, name = icon.split(":", maxsplit=1)
        collection = collections.get(prefix, {}) if isinstance(collections, dict) else {}
        subtitle = None
        if isinstance(collection, dict) and collection.get("name"):
            subtitle = str(collection.get("name"))
        results.append(
            SvgSearchResult(
                source="iconify",
                title=icon,
                svg_url=f"https://api.iconify.design/{prefix}/{name}.svg",
                subtitle=subtitle,
                identifier=icon,
            )
        )
        if len(results) >= limit:
            break
    return results, None


def _search_simple_icons(query: str, *, limit: int) -> tuple[list[SvgSearchResult], str | None]:
    results: list[SvgSearchResult] = []

    for slug in _simple_icon_slug_candidates(query):
        svg_url = f"https://cdn.simpleicons.org/{urllib.parse.quote(slug)}"
        if not _probe_svg_url(svg_url):
            continue
        results.append(
            SvgSearchResult(
                source="simple-icons",
                title=query.strip() or slug,
                svg_url=svg_url,
                subtitle="Simple Icons brand slug",
                identifier=slug,
                verified=True,
            )
        )
        if len(results) >= limit:
            break

    return results, None


def _normalize_sources(sources: Sequence[str] | None) -> tuple[str, ...]:
    if not sources:
        return SUPPORTED_SVG_SOURCES

    normalized: list[str] = []
    for source in sources:
        candidate = source.strip().casefold()
        if candidate not in SUPPORTED_SVG_SOURCES:
            supported = ", ".join(SUPPORTED_SVG_SOURCES)
            raise SvgSearchError(f"Unknown SVG source: {source!r} (choose from {supported})")
        if candidate not in normalized:
            normalized.append(candidate)
    return tuple(normalized)


def search_svg_assets(
    query: str,
    *,
    limit: int = DEFAULT_SVG_RESULT_LIMIT,
    sources: Sequence[str] | None = None,
) -> SvgSearchResponse:
    stripped_query = query.strip()
    if not stripped_query:
        raise SvgSearchError("Query must not be empty")
    if limit < 1:
        raise SvgSearchError("Limit must be at least 1")

    normalized_sources = _normalize_sources(sources)
    warnings: list[str] = []
    results: list[SvgSearchResult] = []
    per_source_limit = max(limit, DEFAULT_SVG_RESULT_LIMIT)

    for source in normalized_sources:
        if source == "svgl":
            source_results, warning = _search_svgl(stripped_query, limit=per_source_limit)
        elif source == "simple-icons":
            source_results, warning = _search_simple_icons(stripped_query, limit=per_source_limit)
        else:
            source_results, warning = _search_iconify(stripped_query, limit=per_source_limit)
        results.extend(source_results)
        if warning:
            warnings.append(warning)

    ranked_results = sorted(
        _dedupe_results(results),
        key=lambda result: _result_score(result, query=stripped_query),
    )
    verified_results = _verify_results(ranked_results, limit=limit)

    if not verified_results and warnings and not results:
        raise SvgSearchError("; ".join(warnings))

    return SvgSearchResponse(query=stripped_query, results=verified_results, warnings=warnings)
