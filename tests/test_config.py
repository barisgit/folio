from __future__ import annotations

from pathlib import Path

from folio.core.dsl.loader import default_spec_path, load_dsl_module, resolve_spec_path
from folio.core.render.pipeline import build_pages


def test_starter_config_uses_expected_page_ids() -> None:
    spec_path = Path("config/folio.py").resolve()

    result = build_pages(load_dsl_module(spec_path), config_dir=spec_path.parent)

    assert [page.page_id for page in result.pages] == ["cover", "notes"]


def test_default_spec_path_uses_build_py(tmp_path: Path) -> None:
    build_path = tmp_path / "build.py"
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "folio.py").write_text("# starter spec\n", encoding="utf-8")

    assert default_spec_path(tmp_path) == build_path


def test_resolve_spec_path_accepts_project_directory(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    build_path = project_dir / "build.py"
    build_path.write_text("# build spec\n", encoding="utf-8")

    assert resolve_spec_path(project_dir) == build_path
