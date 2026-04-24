"""Walk the three public DSL surfaces and produce :class:`Symbol` records."""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from typing import Any

from folio.docs.docstring_parser import ParsedDoc, parse_docstring
from folio.docs.meta import DEFAULT_EXAMPLE_SETUP, DSL_KINDS
from folio.docs.schema import VALID_KINDS, Example, Param, Returns, Symbol
from folio.docs.source_info import public_module_for, resolve_source


class DiscoveryError(RuntimeError):
    """Raised when a public symbol is malformed or misclassified."""


def discover_all() -> list[Symbol]:
    """Return every public DSL symbol sorted by id with duplicates rejected."""
    collected: dict[str, Symbol] = {}
    sources_seen: dict[str, str] = {}
    for symbol in _iter_symbols():
        existing = collected.get(symbol.id)
        if existing is not None:
            if existing.source != symbol.source:
                raise DiscoveryError(
                    f"duplicate symbol id '{symbol.id}' produced by "
                    f"different sources: '{existing.source}' and '{symbol.source}'"
                )
            continue
        collected[symbol.id] = symbol
        sources_seen[symbol.id] = symbol.source
    return sorted(collected.values(), key=lambda sym: sym.id)


def _iter_symbols() -> Iterable[Symbol]:
    from folio import dsl

    yield from _iter_dsl_all(dsl)
    yield from _iter_tokens_surface(dsl.tokens)
    yield from _iter_styles_surface(dsl.tokens.STYLES, tokens_module=dsl.tokens)


def _iter_dsl_all(dsl_module: Any) -> Iterable[Symbol]:
    for name in dsl_module.__all__:
        value = getattr(dsl_module, name)
        if inspect.ismodule(value):
            yield _describe_module(name, value)
            continue
        yield _describe_callable_or_class(name, value, module=public_module_for(name))


def _iter_tokens_surface(tokens_module: Any) -> Iterable[Symbol]:
    for name in sorted(getattr(tokens_module, "__all__", ()) or dir(tokens_module)):
        if name.startswith("_") or name in {"STYLES", "TextStyle"}:
            continue
        value = getattr(tokens_module, name)
        if inspect.ismodule(value):
            continue
        yield _describe_token(name, value, tokens_module=tokens_module)


def _iter_styles_surface(styles: Any, *, tokens_module: Any) -> Iterable[Symbol]:
    for name in sorted(vars(styles)):
        if name.startswith("_"):
            continue
        value = getattr(styles, name)
        yield _describe_style(name, value, tokens_module=tokens_module)


def _describe_module(name: str, module: Any) -> Symbol:
    kind = DSL_KINDS.get(name)
    if kind is None:
        raise DiscoveryError(f"missing kind registry entry for '{name}'")
    _validate_kind(name, kind)
    doc = _require_parsed_doc(
        raw=inspect.getdoc(module),
        symbol=f"folio.dsl.{name}",
        source_hint=f"{module.__name__}:1",
    )
    examples = _ensure_examples(doc.examples)
    return Symbol(
        id=f"folio.dsl.{name}",
        name=name,
        kind=kind,
        module="folio.dsl",
        signature=name,
        summary=doc.summary,
        description=doc.description,
        params=(),
        returns=None,
        examples=examples,
        tags=doc.tags,
        source=f"{module.__name__}:1",
    )


def _describe_callable_or_class(name: str, value: Any, *, module: str) -> Symbol:
    kind = DSL_KINDS.get(name)
    if kind is None:
        raise DiscoveryError(f"missing kind registry entry for '{name}'")
    _validate_kind(name, kind)
    source = _resolve_source_safely(value, symbol=f"{module}.{name}")
    raw_doc = inspect.getdoc(value)
    doc = _require_parsed_doc(
        raw=raw_doc,
        symbol=f"{module}.{name}",
        source_hint=source,
    )
    signature, params, returns_annotation = _render_signature(name, value)
    params_with_docs = _merge_param_docs(params, doc.params)
    returns = _build_returns(returns_annotation, doc.returns_doc)
    examples = _ensure_examples(doc.examples, default_setup_required=False)
    return Symbol(
        id=f"{module}.{name}",
        name=name,
        kind=kind,
        module=module,
        signature=signature,
        summary=doc.summary,
        description=doc.description,
        params=tuple(params_with_docs),
        returns=returns,
        examples=examples,
        tags=doc.tags,
        source=source,
    )


def _describe_token(name: str, value: Any, *, tokens_module: Any) -> Symbol:
    from folio.docs.meta import TOKEN_DOCS  # noqa: PLC0415

    kind: str
    if callable(value):
        kind = "helper"
    else:
        kind = "token"
    _validate_kind(name, kind)

    source = _resolve_source_safely(
        value,
        symbol=f"folio.dsl.tokens.{name}",
        fallback=f"{tokens_module.__name__}:1",
    )

    if callable(value) and not isinstance(value, type(tokens_module)):
        raw_doc = inspect.getdoc(value)
        doc = _require_parsed_doc(
            raw=raw_doc,
            symbol=f"folio.dsl.tokens.{name}",
            source_hint=source,
        )
        signature, params, returns_annotation = _render_signature(name, value)
        params_with_docs = _merge_param_docs(params, doc.params)
        returns = _build_returns(returns_annotation, doc.returns_doc)
        summary = doc.summary
        description = doc.description
        examples = _ensure_examples(doc.examples, default_setup_required=False)
        tags = doc.tags
    else:
        entry = TOKEN_DOCS.get(name)
        if entry is None:
            raise DiscoveryError(
                f"token 'folio.dsl.tokens.{name}' is missing a TOKEN_DOCS entry "
                f"({source})"
            )
        summary = entry["summary"]
        description = entry.get("description", "")
        signature = _render_token_signature(name, value)
        params_with_docs = ()
        returns = None
        examples = _ensure_examples(
            tuple(
                Example(code=code, caption=caption, setup=None)
                for code, caption in entry.get("examples", [])
            )
        )
        tags = tuple(entry.get("tags", ()))

    return Symbol(
        id=f"folio.dsl.tokens.{name}",
        name=name,
        kind=kind,
        module="folio.dsl.tokens",
        signature=signature,
        summary=summary,
        description=description,
        params=tuple(params_with_docs),
        returns=returns,
        examples=examples,
        tags=tags,
        source=source,
    )


def _describe_style(name: str, value: Any, *, tokens_module: Any) -> Symbol:
    from folio.docs.meta import STYLE_DOCS  # noqa: PLC0415

    _validate_kind(name, "style")
    entry = STYLE_DOCS.get(name)
    if entry is None:
        raise DiscoveryError(
            f"style 'folio.dsl.tokens.STYLES.{name}' is missing a STYLE_DOCS entry"
        )
    source = _resolve_source_safely(
        value,
        symbol=f"folio.dsl.tokens.STYLES.{name}",
        fallback=f"{tokens_module.__name__}:1",
    )
    examples = _ensure_examples(
        tuple(
            Example(code=code, caption=caption, setup=None)
            for code, caption in entry.get("examples", [])
        )
    )
    return Symbol(
        id=f"folio.dsl.tokens.STYLES.{name}",
        name=name,
        kind="style",
        module="folio.dsl.tokens.STYLES",
        signature=_render_style_signature(name, value),
        summary=entry["summary"],
        description=entry.get("description", ""),
        params=(),
        returns=None,
        examples=examples,
        tags=tuple(entry.get("tags", ())),
        source=source,
    )


def _validate_kind(name: str, kind: str) -> None:
    if kind not in VALID_KINDS:
        raise DiscoveryError(
            f"symbol '{name}' declared kind '{kind}' not in closed enum {VALID_KINDS}"
        )


def _require_parsed_doc(*, raw: str | None, symbol: str, source_hint: str) -> ParsedDoc:
    parsed = parse_docstring(raw)
    if parsed is None or not parsed.summary:
        raise DiscoveryError(
            f"public DSL symbol '{symbol}' has no docstring ({source_hint})"
        )
    if _looks_like_dataclass_autodoc(parsed.summary, symbol):
        raise DiscoveryError(
            f"public DSL symbol '{symbol}' uses an auto-synthesized dataclass "
            f"docstring; add a real docstring ({source_hint})"
        )
    return parsed


def _looks_like_dataclass_autodoc(summary: str, symbol: str) -> bool:
    class_name = symbol.rsplit(".", 1)[-1]
    return summary.startswith(f"{class_name}(") and summary.rstrip().endswith(")")


def _ensure_examples(
    examples: tuple[Example, ...], *, default_setup_required: bool = False
) -> tuple[Example, ...]:
    _ = default_setup_required
    return tuple(
        Example(
            code=example.code,
            caption=example.caption,
            setup=example.setup if example.setup is not None else DEFAULT_EXAMPLE_SETUP,
        )
        for example in examples
    )


def _render_signature(name: str, value: Any) -> tuple[str, list[Param], str]:
    try:
        sig = inspect.signature(value)
    except (TypeError, ValueError):
        return (name, [], "")
    params: list[Param] = []
    for param in sig.parameters.values():
        annotation = _render_annotation(param.annotation, fallback="Any")
        params.append(Param(name=param.name, type=annotation, doc=""))
    returns_annotation = _render_annotation(sig.return_annotation, fallback="")
    rendered = f"{name}{sig}"
    return rendered, params, returns_annotation


def _render_annotation(annotation: Any, *, fallback: str) -> str:
    if annotation is inspect.Signature.empty or annotation is inspect.Parameter.empty:
        return fallback
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__name__", None) or repr(annotation)


def _render_token_signature(name: str, value: Any) -> str:
    if isinstance(value, str):
        return f"{name}: str = {value!r}"
    if isinstance(value, (int, float)):
        return f"{name}: {type(value).__name__} = {value!r}"
    if isinstance(value, dict):
        keys = ", ".join(value.keys())
        return f"{name}: dict = {{{keys}}}"
    return f"{name}: {type(value).__name__}"


def _render_style_signature(name: str, value: Any) -> str:
    attrs = []
    for slot in ("font_size_pt", "font_weight", "fill", "letter_spacing", "font_family"):
        if hasattr(value, slot):
            attr_value = getattr(value, slot)
            if attr_value is not None:
                attrs.append(f"{slot}={attr_value!r}")
    return f"{name} = TextStyle({', '.join(attrs)})"


def _merge_param_docs(params: list[Param], docs: dict[str, str]) -> list[Param]:
    merged: list[Param] = []
    for param in params:
        doc = docs.get(param.name, "")
        merged.append(Param(name=param.name, type=param.type, doc=doc))
    return merged


def _build_returns(annotation: str, doc_text: str) -> Returns | None:
    if not annotation and not doc_text:
        return None
    return Returns(type=annotation, doc=doc_text)


def _resolve_source_safely(value: Any, *, symbol: str, fallback: str = "") -> str:
    try:
        return resolve_source(value)
    except Exception as exc:  # noqa: BLE001 — we re-raise with context below
        if fallback:
            return fallback
        raise DiscoveryError(f"cannot resolve source for '{symbol}': {exc}") from exc
