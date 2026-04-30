"""CLI integration tests for tweak-aware validate/build."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from folio.cli import app

runner = CliRunner()


SPEC_WITH_TWEAKS = dedent(
    """
    from folio.dsl import TextStyle, page, render, text, tweaks

    theme = tweaks.group(
        "theme",
        primary=tweaks.color(default="#d9a64b"),
        hero_size_pt=tweaks.size_pt(default=58, min=32, max=76),
    )

    HERO = TextStyle(font_size_pt=theme.hero_size_pt, fill=theme.primary)


    def build():
        return render(
            page(
                page_id="one",
                filename="one.svg",
                page_number=1,
                elements=[text("hero", 10, 20, "Hi", style=HERO)],
            ),
        )
    """
).strip() + "\n"


def _write_spec(tmp_path: Path, body: str = SPEC_WITH_TWEAKS) -> Path:
    spec_path = tmp_path / "spec.py"
    spec_path.write_text(body, encoding="utf-8")
    return spec_path


def _write_values(tmp_path: Path, content: str) -> Path:
    values_path = tmp_path / "theme.toml"
    values_path.write_text(content, encoding="utf-8")
    return values_path


def test_validate_passes_with_valid_persisted_value(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    _write_values(tmp_path, '[theme]\nprimary = "#112233"\nhero_size_pt = 60\n')

    command = runner.invoke(app, ["validate", str(spec_path)])

    assert command.exit_code == 0, command.output
    assert "valid" in command.output


def test_validate_fails_on_invalid_type(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    _write_values(tmp_path, '[theme]\nhero_size_pt = "huge"\n')

    command = runner.invoke(app, ["validate", str(spec_path)])

    assert command.exit_code != 0
    assert "theme.hero_size_pt" in command.output
    # The values-file path is included; rich may line-wrap it, so just check
    # the filename is mentioned.
    assert "theme.toml" in command.output


def test_validate_fails_on_out_of_range(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    _write_values(tmp_path, "[theme]\nhero_size_pt = 200\n")

    command = runner.invoke(app, ["validate", str(spec_path)])

    assert command.exit_code != 0
    assert "theme.hero_size_pt" in command.output
    # Range hint should mention either the min or max bound.
    assert "32" in command.output or "76" in command.output


def test_validate_warns_on_unknown_persisted_key(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    _write_values(
        tmp_path,
        '[theme]\nprimary = "#112233"\nold_value = "stale"\n',
    )

    command = runner.invoke(app, ["validate", str(spec_path)])

    assert command.exit_code == 0, command.output
    assert "warning" in command.output.lower()
    assert "theme.old_value" in command.output


def test_validate_succeeds_for_spec_without_tweaks(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path,
        dedent(
            """
            from folio.dsl import page, render, text

            def build():
                return render(
                    page(
                        page_id="one",
                        filename="one.svg",
                        page_number=1,
                        elements=[text("hero", 10, 20, "Hi", size_pt=12)],
                    ),
                )
            """
        ).strip() + "\n",
    )
    # Note: no theme.toml on disk.
    command = runner.invoke(app, ["validate", str(spec_path)])

    assert command.exit_code == 0, command.output


def test_build_uses_persisted_color_in_rendered_svg(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    _write_values(tmp_path, '[theme]\nprimary = "#112233"\nhero_size_pt = 60\n')
    out_dir = tmp_path / "out"

    command = runner.invoke(
        app,
        ["build", str(spec_path), "--out-dir", str(out_dir), "--no-cache"],
    )

    assert command.exit_code == 0, command.output
    rendered = (out_dir / "one.svg").read_text(encoding="utf-8")
    assert "#112233" in rendered


def test_build_aborts_on_invalid_value(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    _write_values(tmp_path, "[theme]\nhero_size_pt = 200\n")
    out_dir = tmp_path / "out"

    command = runner.invoke(
        app,
        ["build", str(spec_path), "--out-dir", str(out_dir), "--no-cache"],
    )

    assert command.exit_code != 0
    assert "theme.hero_size_pt" in command.output
    assert not out_dir.exists() or not any(out_dir.iterdir())


def test_build_for_spec_without_theme_toml_succeeds(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    out_dir = tmp_path / "out"

    command = runner.invoke(
        app,
        ["build", str(spec_path), "--out-dir", str(out_dir), "--no-cache"],
    )

    assert command.exit_code == 0, command.output
    rendered = (out_dir / "one.svg").read_text(encoding="utf-8")
    # Default color from declaration should be present.
    assert "#d9a64b" in rendered
