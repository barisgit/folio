from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from folio.cli import app

runner = CliRunner()


def test_create_rejects_invalid_var_format(tmp_path: Path) -> None:
    command = runner.invoke(app, ["create", str(tmp_path / "my-doc"), "--var", "brand_name"])

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
    assert (project_dir / "assets").is_dir()
    assert (project_dir / "assets" / "hero_typography.jpg").exists()
    assert (project_dir / "assets" / "icon_chart.svg").exists()
    assert not (project_dir / "template.yaml").exists()
    content = (project_dir / "content.py").read_text(encoding="utf-8")
    assert 'BRAND_NAME = "FOLIO STUDIO"' in content
    assert 'DOCUMENT_KICKER = "STARTER KIT  /  ISSUE 01  /  SPRING 2026"' in content


def test_create_starter_template_builds_end_to_end(tmp_path: Path) -> None:
    project_dir = tmp_path / "my-doc"

    create_command = runner.invoke(
        app,
        [
            "create",
            str(project_dir),
            "--var",
            "brand_name=ACME",
            "--var",
            "document_title=Ship layouts from Python.",
            "--var",
            "document_kicker=STARTER TEMPLATE",
        ],
    )

    assert create_command.exit_code == 0
    assert (project_dir / "build.py").exists()
    assert (project_dir / "pages.py").exists()
    assert (project_dir / "layout.py").exists()
    assert (project_dir / "theme.py").exists()
    assert (project_dir / "content.py").exists()
    assert (project_dir / ".gitignore").exists()
    assert (project_dir / "assets").is_dir()
    assert (project_dir / "assets" / "hero_typography.jpg").exists()
    assert (project_dir / "assets" / "icon_chart.svg").exists()
    assert "ACME" in (project_dir / "content.py").read_text(encoding="utf-8")

    build_command = runner.invoke(app, ["build", str(project_dir), "--no-cache"])

    assert build_command.exit_code == 0
    assert (project_dir / "out" / "01_cover.svg").exists()
    assert (project_dir / "out" / "02_features.svg").exists()
    assert (project_dir / "out" / "03_metrics.svg").exists()
