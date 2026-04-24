"""JSON serialization for the doc index."""

from __future__ import annotations

import json

from folio.services.docs.schema import Index


def dumps(index: Index) -> str:
    """Return a stable JSON representation of `index`.

    Key order is fixed by the schema's `to_dict` method. Symbols are
    ordered by id (done at discovery time).
    """
    data = index.to_dict()
    return json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False) + "\n"


def loads(text: str) -> dict[str, object]:
    """Return the parsed JSON payload of an index string."""
    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError("doc index must deserialize into a JSON object")
    return loaded
