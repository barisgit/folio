from __future__ import annotations

from pathlib import Path

from folio.core.dsl.loader import load_dsl_module
from folio.core.render.pipeline import build_pages, write_pages


def test_bundled_folio_config_builds_standalone() -> None:
    spec_path = Path("config/folio.py").resolve()

    result = build_pages(load_dsl_module(spec_path), config_dir=spec_path.parent)

    assert result.config_hash
    assert [page.filename for page in result.pages] == ["cover.svg", "notes.svg"]

    cover = result.pages[0].content
    notes = result.pages[1].content

    assert 'data-page-number="1"' in cover
    assert 'data-page-id="cover"' in cover
    assert 'id="cover_bg"' in cover
    assert 'id="cover_title"' in cover
    assert "folio" in cover

    assert 'data-page-number="2"' in notes
    assert 'data-page-id="notes"' in notes
    assert 'id="notes_title"' in notes
    assert 'id="notes_body_line_3"' in notes
    assert "to folio build." in notes


def test_bundled_folio_config_build_is_idempotent(tmp_path: Path) -> None:
    spec_path = Path("config/folio.py").resolve()

    first = build_pages(load_dsl_module(spec_path), config_dir=spec_path.parent)
    second = build_pages(load_dsl_module(spec_path), config_dir=spec_path.parent)

    assert first.config_hash == second.config_hash
    assert [
        (page.page_number, page.page_id, page.filename, page.content) for page in first.pages
    ] == [(page.page_number, page.page_id, page.filename, page.content) for page in second.pages]

    first_paths = write_pages(first, tmp_path / "first")
    second_paths = write_pages(second, tmp_path / "second")

    assert [path.name for path in first_paths] == [path.name for path in second_paths]
    for first_path, second_path in zip(first_paths, second_paths, strict=True):
        assert first_path.read_bytes() == second_path.read_bytes()
