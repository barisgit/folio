"""Schema v1 for the Folio DSL documentation index.

The schema is the contract between the generator and every consumer
(`folio docs`, the build-time guard, CI staleness checks). Breaking changes
bump `INDEX_SCHEMA_VERSION` and readers reject indices they do not
understand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

INDEX_SCHEMA_VERSION = 1

Kind = Literal["primitive", "defs", "token", "style", "builder", "helper"]
VALID_KINDS: tuple[str, ...] = (
    "primitive",
    "defs",
    "token",
    "style",
    "builder",
    "helper",
)


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    type: str
    doc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "doc": self.doc}


@dataclass(frozen=True, slots=True)
class Returns:
    type: str
    doc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "doc": self.doc}


@dataclass(frozen=True, slots=True)
class Example:
    code: str
    caption: str | None = None
    setup: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "caption": self.caption, "setup": self.setup}


@dataclass(frozen=True, slots=True)
class Symbol:
    id: str
    name: str
    kind: str
    module: str
    signature: str
    summary: str
    source: str
    description: str = ""
    params: tuple[Param, ...] = field(default_factory=tuple)
    returns: Returns | None = None
    examples: tuple[Example, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "module": self.module,
            "signature": self.signature,
            "summary": self.summary,
            "description": self.description,
            "params": [param.to_dict() for param in self.params],
            "returns": self.returns.to_dict() if self.returns is not None else None,
            "examples": [example.to_dict() for example in self.examples],
            "tags": list(self.tags),
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class Index:
    version: int
    generated_at: str
    folio_version: str
    symbols: tuple[Symbol, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "folio_version": self.folio_version,
            "symbols": [symbol.to_dict() for symbol in self.symbols],
        }
