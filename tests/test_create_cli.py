from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from folio.cli import app

runner = CliRunner()


def test_create_rejects_invalid_var_format(tmp_path: Path) -> None:
    command = runner.invoke(app, ["create", str(tmp_path / "my-doc"), "--var", "project_slug"])

    assert command.exit_code == 1


def test_create_rejects_non_empty_target(tmp_path: Path) -> None:
    target = tmp_path / "output"
    target.mkdir()
    (target / "existing.txt").write_text("already here", encoding="utf-8")

    command = runner.invoke(app, ["create", str(target)])

    assert command.exit_code == 1


def test_create_uses_builtin_defaults(tmp_path: Path) -> None:
    project_dir = tmp_path / "my-doc"

    command = runner.invoke(app, ["create", str(project_dir)])

    assert command.exit_code == 0
    assert (project_dir / "build.py").exists()
    assert (project_dir / "pages.py").exists()
    assert (project_dir / "layout.py").exists()
    assert (project_dir / "theme.py").exists()
    assert (project_dir / "content.py").exists()
    assert (project_dir / ".gitignore").exists()
    assert (project_dir / "pyproject.toml").exists()
    assert (project_dir / "README.md").exists()
    assert (project_dir / "assets").is_dir()
    assert (project_dir / "assets" / "hero_typography.jpg").exists()
    assert (project_dir / "assets" / "icon_chart.svg").exists()
    assert not (project_dir / "template.yaml").exists()
    content = (project_dir / "content.py").read_text(encoding="utf-8")
    assert 'BRAND_NAME = "FOLIO STUDIO"' in content
    assert 'DOCUMENT_KICKER = "STARTER KIT  /  ISSUE 01  /  SPRING 2026"' in content
    pyproject = (project_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "my-doc"' in pyproject
    assert "[tool.ruff]" in pyproject
    assert "[tool.ruff.lint]" in pyproject


def test_create_starter_template_builds_end_to_end(tmp_path: Path) -> None:
    project_dir = tmp_path / "acme-brochure"

    create_command = runner.invoke(app, ["create", str(project_dir)])

    assert create_command.exit_code == 0
    assert (project_dir / "build.py").exists()
    assert (project_dir / "pages.py").exists()
    assert (project_dir / "layout.py").exists()
    assert (project_dir / "theme.py").exists()
    assert (project_dir / "content.py").exists()
    assert (project_dir / ".gitignore").exists()
    assert (project_dir / "pyproject.toml").exists()
    assert (project_dir / "README.md").exists()
    assert (project_dir / "assets").is_dir()
    assert (project_dir / "assets" / "hero_typography.jpg").exists()
    assert (project_dir / "assets" / "icon_chart.svg").exists()
    pyproject = (project_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "acme-brochure"' in pyproject

    build_command = runner.invoke(app, ["build", str(project_dir), "--no-cache"])

    assert build_command.exit_code == 0
    assert (project_dir / "out" / "01_cover.svg").exists()
    assert (project_dir / "out" / "02_features.svg").exists()
    assert (project_dir / "out" / "03_metrics.svg").exists()


def test_create_accepts_project_slug_override(tmp_path: Path) -> None:
    project_dir = tmp_path / "my-doc"

    command = runner.invoke(
        app,
        ["create", str(project_dir), "--var", "project_slug=custom-slug"],
    )

    assert command.exit_code == 0
    pyproject = (project_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "custom-slug"' in pyproject
