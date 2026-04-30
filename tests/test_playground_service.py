"""Tests for server-independent playground state/persistence service."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from folio.core.cache import cache_build, cache_paths
from folio.services.playground import (
    PlaygroundUpdateError,
    apply_tweak_update,
    load_playground_state,
)
from folio.services.tweaks_load import load_spec_with_tweaks


SPEC_WITH_TWEAKS = dedent(
    """
    from folio.dsl import TextStyle, collection, document, page, rect, text, tweaks

    theme = tweaks.group(
        "theme",
        primary=tweaks.color(default="#d9a64b"),
        hero_size_pt=tweaks.size_pt(default=58, min=32, max=76),
        panel_width=tweaks.size_mm(default=40),
        rebuilt=tweaks.color(default="#112233", mode="rebuild"),
    )

    HERO = TextStyle(font_size_pt=theme.hero_size_pt, fill=theme.primary)


    def build():
        return collection(
            document(
                "demo",
                pages=[
                    page(
                        page_id="one",
                        filename="one.svg",
                        page_number=1,
                        elements=[
                            rect("panel", 0, 0, theme.panel_width, 20, fill=theme.rebuilt),
                            text("hero", 10, 20, "Hi", style=HERO),
                        ],
                    )
                ],
            )
        )
    """
).strip() + "\n"


SPEC_WITHOUT_TWEAKS = dedent(
    """
    from folio.dsl import collection, document, page, text


    def build():
        return collection(
            document(
                "demo",
                pages=[
                    page(
                        page_id="one",
                        filename="one.svg",
                        page_number=1,
                        elements=[text("hero", 10, 20, "Hi", size_pt=12)],
                    )
                ],
            )
        )
    """
).strip() + "\n"


def _write_spec(tmp_path: Path, body: str = SPEC_WITH_TWEAKS) -> Path:
    spec_path = tmp_path / "build.py"
    spec_path.write_text(body, encoding="utf-8")
    return spec_path


def _write_values(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "theme.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_playground_state_includes_pages_declarations_values_and_css_vars(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    _write_values(tmp_path, '[theme]\nprimary = "#445566"\nhero_size_pt = 64\n')

    state = load_playground_state(spec_path)

    assert state.spec_path == spec_path.resolve()
    assert state.values_path == tmp_path / "theme.toml"
    assert len(state.pages) == 1
    assert state.pages[0].filename == "one.svg"
    assert 'fill="var(--folio-tweak-theme-primary, #445566)"' in state.pages[0].svg
    assert 'font-size="var(--folio-tweak-theme-hero-size-pt, 64.0pt)"' in state.pages[0].svg
    assert 'fill="#112233"' in state.pages[0].svg
    assert "var(--folio-tweak-theme-panel-width" not in state.pages[0].svg
    assert state.values["theme.primary"] == "#445566"
    assert state.values["theme.hero_size_pt"] == 64.0
    schema = {tweak.key: tweak for tweak in state.tweaks}
    assert schema["theme.primary"].kind == "color"
    assert schema["theme.primary"].mode == "live"
    assert schema["theme.primary"].css_var == "--folio-tweak-theme-primary"
    assert schema["theme.hero_size_pt"].min == 32
    assert schema["theme.hero_size_pt"].max == 76


def test_repeated_playground_load_reexecutes_imported_theme_module(tmp_path: Path) -> None:
    (tmp_path / "theme.py").write_text(
        dedent(
            """
            from folio.dsl import TextStyle, tweaks

            theme = tweaks.group(
                "theme",
                primary=tweaks.color(default="#d9a64b"),
                hero_size_pt=tweaks.size_pt(default=58, min=32, max=76),
            )
            HERO = TextStyle(font_size_pt=theme.hero_size_pt, fill=theme.primary)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    spec_path = _write_spec(
        tmp_path,
        dedent(
            """
            from folio.dsl import collection, document, page, text
            from theme import HERO

            def build():
                return collection(
                    document(
                        "demo",
                        pages=[
                            page(
                                page_id="one",
                                filename="one.svg",
                                page_number=1,
                                elements=[text("hero", 10, 20, "Hi", style=HERO)],
                            )
                        ],
                    )
                )
            """
        ).strip()
        + "\n",
    )
    _write_values(tmp_path, '[theme]\nprimary = "#445566"\nhero_size_pt = 64\n')

    first = load_playground_state(spec_path)
    second = load_playground_state(spec_path)

    assert [tweak.key for tweak in first.tweaks] == ["theme.primary", "theme.hero_size_pt"]
    assert [tweak.key for tweak in second.tweaks] == ["theme.primary", "theme.hero_size_pt"]
    assert second.diagnostics == ()
    assert 'fill="var(--folio-tweak-theme-primary, #445566)"' in second.pages[0].svg


def test_playground_state_for_spec_without_tweaks_is_valid_and_empty(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path, SPEC_WITHOUT_TWEAKS)

    state = load_playground_state(spec_path)

    assert len(state.pages) == 1
    assert state.tweaks == ()
    assert dict(state.values) == {}
    assert state.diagnostics == ()


def test_apply_tweak_update_writes_deterministic_toml_and_returns_fresh_state(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    state = apply_tweak_update(
        spec_path,
        {
            "theme.hero_size_pt": 70,
            "theme.primary": "#ff3366",
        },
    )

    assert (tmp_path / "theme.toml").read_text(encoding="utf-8") == dedent(
        """
        [theme]
        hero_size_pt = 70.0
        panel_width = 40.0
        primary = "#ff3366"
        rebuilt = "#112233"
        """
    ).lstrip()
    assert state.values["theme.primary"] == "#ff3366"
    assert state.values["theme.hero_size_pt"] == 70.0
    assert 'var(--folio-tweak-theme-primary, #ff3366)' in state.pages[0].svg
    assert 'var(--folio-tweak-theme-hero-size-pt, 70.0pt)' in state.pages[0].svg


def test_apply_tweak_update_accepts_single_key_value_form(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    state = apply_tweak_update(spec_path, key="theme.primary", value="#abcdef")

    assert state.values["theme.primary"] == "#abcdef"
    assert 'primary = "#abcdef"' in (tmp_path / "theme.toml").read_text(
        encoding="utf-8"
    )


def test_invalid_tweak_update_rejects_without_changing_file(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    values_path = _write_values(tmp_path, '[theme]\nprimary = "#445566"\nhero_size_pt = 64\n')
    before = values_path.read_text(encoding="utf-8")

    with pytest.raises(PlaygroundUpdateError) as exc_info:
        apply_tweak_update(spec_path, {"theme.hero_size_pt": 120})

    assert "theme.hero_size_pt" in str(exc_info.value)
    assert values_path.read_text(encoding="utf-8") == before


def test_unknown_tweak_update_rejects_without_changing_file(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    values_path = _write_values(tmp_path, '[theme]\nprimary = "#445566"\n')
    before = values_path.read_text(encoding="utf-8")

    with pytest.raises(PlaygroundUpdateError) as exc_info:
        apply_tweak_update(spec_path, {"theme.missing": "nope"})

    assert "unknown tweak key" in str(exc_info.value)
    assert values_path.read_text(encoding="utf-8") == before


def test_last_write_wins_rereads_external_edit_before_update(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    values_path = _write_values(tmp_path, '[theme]\nprimary = "#111111"\nhero_size_pt = 60\n')

    # Simulate an external editor changing the file before the playground
    # submits its next accepted edit. The service rereads and merges with
    # the current file contents before overwriting deterministically.
    values_path.write_text('[theme]\nprimary = "#222222"\nhero_size_pt = 60\n', encoding="utf-8")

    state = apply_tweak_update(spec_path, {"theme.hero_size_pt": 68})

    assert state.values["theme.primary"] == "#222222"
    assert state.values["theme.hero_size_pt"] == 68.0
    written = values_path.read_text(encoding="utf-8")
    assert 'primary = "#222222"' in written
    assert "hero_size_pt = 68.0" in written


def test_playground_state_and_update_do_not_create_last_build_cache(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    paths = cache_paths(spec_path.resolve())
    assert not paths.root.exists()

    load_playground_state(spec_path)
    apply_tweak_update(spec_path, {"theme.primary": "#ff3366"})

    assert not paths.root.exists()


def test_playground_state_and_update_do_not_modify_existing_last_build_cache(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    build_outcome = load_spec_with_tweaks(spec_path.resolve())
    cached = cache_build(build_outcome.result, spec_path=spec_path.resolve())
    before_manifest = cached.manifest.read_text(encoding="utf-8")
    before_page = cached.page_map[1].read_text(encoding="utf-8")

    load_playground_state(spec_path)
    apply_tweak_update(spec_path, {"theme.primary": "#ff3366"})

    assert cached.manifest.read_text(encoding="utf-8") == before_manifest
    assert cached.page_map[1].read_text(encoding="utf-8") == before_page
