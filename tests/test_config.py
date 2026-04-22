from __future__ import annotations

from pathlib import Path

from folio.dsl.loader import load_dsl_module
from folio.dsl.renderer import build_pages


def test_starter_config_uses_expected_page_ids() -> None:
    spec_path = Path("config/folio.py").resolve()

    result = build_pages(load_dsl_module(spec_path), config_dir=spec_path.parent)

    assert [page.page_id for page in result.pages] == ["cover", "notes"]
