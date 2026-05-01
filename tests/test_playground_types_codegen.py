"""Drift detection: the committed ``api.generated.ts`` must match a fresh
run of the codegen helper, character-for-character.

When a Pydantic model changes (new field, alias, type), running
``bun run build:playground`` rewrites the file. This test fails until the
maintainer runs that command and commits the regenerated file.
"""

from __future__ import annotations

from pathlib import Path

from folio._dev.gen_playground_types import _OUTPUT_PATH, render_typescript

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_committed_api_generated_ts_matches_codegen() -> None:
    target = _REPO_ROOT / _OUTPUT_PATH
    assert target.exists(), (
        f"{_OUTPUT_PATH} is missing. Run `bun run build:playground`."
    )

    actual = target.read_text(encoding="utf-8")
    expected = render_typescript()
    assert actual == expected, (
        "src/folio/playground_ui/api.generated.ts is out of date. "
        "Run `bun run build:playground` and commit the regenerated file."
    )
