from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from folio.core.dsl import tweaks
from folio.core.dsl.tweak_values import (
    TweakValuesError,
    apply_persisted_values,
    load_persisted_values,
    resolve_values_file,
    validate_persisted_values,
    write_persisted_values,
)
from folio.core.dsl.tweaks import TweakRegistry, normalize_color, tweak_context


# ---------------------------------------------------------------------------
# resolve_values_file
# ---------------------------------------------------------------------------


def test_resolve_values_file_is_sibling_theme_toml(tmp_path: Path) -> None:
    spec = tmp_path / "build.py"
    assert resolve_values_file(spec) == tmp_path / "theme.toml"


def test_resolve_values_file_takes_no_override_kwargs(tmp_path: Path) -> None:
    # The signature is intentionally narrow. Adding a values_file= override
    # belongs to a future change, not slice 2.
    with pytest.raises(TypeError):
        resolve_values_file(tmp_path / "build.py", values_file="custom.toml")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# load_persisted_values
# ---------------------------------------------------------------------------


def test_load_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_persisted_values(tmp_path / "absent.toml") is None


def test_load_parses_grouped_tables(tmp_path: Path) -> None:
    path = tmp_path / "theme.toml"
    path.write_text(
        textwrap.dedent(
            """
            [theme]
            primary = "#abcdef"
            hero = 64

            [layout]
            gap_mm = 12
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    raw = load_persisted_values(path)
    assert raw == {
        "theme": {"primary": "#abcdef", "hero": 64},
        "layout": {"gap_mm": 12},
    }


def test_load_rejects_top_level_scalar(tmp_path: Path) -> None:
    path = tmp_path / "theme.toml"
    path.write_text('primary = "#abcdef"\n', encoding="utf-8")
    with pytest.raises(TweakValuesError, match="top-level scalar"):
        load_persisted_values(path)


def test_load_reports_parse_error_with_path(tmp_path: Path) -> None:
    path = tmp_path / "theme.toml"
    path.write_text("[theme\nprimary = \n", encoding="utf-8")
    with pytest.raises(TweakValuesError, match=str(path)):
        load_persisted_values(path)


# ---------------------------------------------------------------------------
# validate_persisted_values
# ---------------------------------------------------------------------------


def _make_registry() -> TweakRegistry:
    registry = TweakRegistry()
    with tweak_context(registry):
        tweaks.group(
            "theme",
            primary=tweaks.color(default="#111111"),
            hero=tweaks.size_pt(default=58, min=32, max=76),
        )
        tweaks.group(
            "layout",
            density=tweaks.choice(default="comfortable", options=("comfortable", "dense")),
            gap_mm=tweaks.size_mm(default=8, min=4, max=16),
        )
    return registry


def test_validate_accepts_valid_values(tmp_path: Path) -> None:
    registry = _make_registry()
    raw = {
        "theme": {"primary": "#abcdef", "hero": 64},
        "layout": {"density": "dense", "gap_mm": 12},
    }
    validated, diags = validate_persisted_values(registry, raw, source=tmp_path / "theme.toml")
    assert diags == []
    assert validated == {
        "theme.primary": "#abcdef",
        "theme.hero": 64.0,
        "layout.density": "dense",
        "layout.gap_mm": 12.0,
    }


def test_validate_rejects_wrong_type_for_numeric() -> None:
    registry = _make_registry()
    raw = {"theme": {"hero": "large"}}
    validated, diags = validate_persisted_values(registry, raw, source=None)
    assert "theme.hero" not in validated
    assert len(diags) == 1
    assert diags[0].severity == "error"
    assert diags[0].key == "theme.hero"
    assert "expects a number" in diags[0].message


def test_validate_rejects_bool_for_numeric() -> None:
    """``isinstance(True, int)`` is true; the validator must reject bools."""

    registry = _make_registry()
    raw = {"theme": {"hero": True}}
    _, diags = validate_persisted_values(registry, raw, source=None)
    assert len(diags) == 1
    assert diags[0].severity == "error"
    assert diags[0].key == "theme.hero"


def test_validate_rejects_out_of_range() -> None:
    registry = _make_registry()
    raw = {"theme": {"hero": 120}}
    _, diags = validate_persisted_values(registry, raw, source=None)
    assert len(diags) == 1
    assert diags[0].severity == "error"
    assert "above max=76" in diags[0].message
    assert "32..76" in diags[0].message


def test_validate_warns_on_unknown_key(tmp_path: Path) -> None:
    registry = _make_registry()
    raw = {"theme": {"primary": "#222222", "ghost": "#333333"}}
    validated, diags = validate_persisted_values(
        registry, raw, source=tmp_path / "theme.toml"
    )
    assert "theme.primary" in validated
    assert "theme.ghost" not in validated
    warnings = [d for d in diags if d.severity == "warning"]
    assert len(warnings) == 1
    assert warnings[0].key == "theme.ghost"
    assert str(tmp_path / "theme.toml") in warnings[0].message


def test_validate_rejects_choice_mismatch() -> None:
    registry = _make_registry()
    raw = {"layout": {"density": "spacious"}}
    _, diags = validate_persisted_values(registry, raw, source=None)
    assert len(diags) == 1
    assert diags[0].severity == "error"
    assert "not in options" in diags[0].message


def test_validate_rejects_non_string_choice() -> None:
    registry = _make_registry()
    raw = {"layout": {"density": 1}}
    _, diags = validate_persisted_values(registry, raw, source=None)
    assert len(diags) == 1
    assert diags[0].severity == "error"


def test_validate_rejects_non_string_color() -> None:
    registry = _make_registry()
    raw = {"theme": {"primary": 0xABCDEF}}
    _, diags = validate_persisted_values(registry, raw, source=None)
    assert len(diags) == 1
    assert diags[0].severity == "error"


def test_validate_normalizes_color() -> None:
    registry = _make_registry()
    raw = {"theme": {"primary": "#ABC"}}
    validated, diags = validate_persisted_values(registry, raw, source=None)
    assert diags == []
    expected = normalize_color("#ABC", kind="color")
    assert validated["theme.primary"] == expected


def test_validate_diagnostics_appended_to_registry() -> None:
    registry = _make_registry()
    raw = {"theme": {"hero": "large"}}
    _, diags = validate_persisted_values(registry, raw, source=None)
    assert registry.diagnostics == diags


def test_validate_handles_none_raw() -> None:
    registry = _make_registry()
    validated, diags = validate_persisted_values(registry, None, source=None)
    assert validated == {}
    assert diags == []


# ---------------------------------------------------------------------------
# apply_persisted_values + TweakValue live read
# ---------------------------------------------------------------------------


def test_apply_persisted_values_propagates_to_existing_tweak_values(tmp_path: Path) -> None:
    spec = tmp_path / "build.py"
    spec.write_text("# placeholder\n", encoding="utf-8")
    (tmp_path / "theme.toml").write_text(
        '[theme]\nprimary = "#abcdef"\nhero = 64\n', encoding="utf-8"
    )

    registry = TweakRegistry()
    with tweak_context(registry):
        # Simulate the order of operations slice 3 will use: declarations
        # register first; persisted values are applied after.
        theme = tweaks.group(
            "theme",
            primary=tweaks.color(default="#111111"),
            hero=tweaks.size_pt(default=58, min=32, max=76),
        )
        # Wrappers initially see defaults.
        assert str(theme.primary) == "#111111"
        assert float(theme.hero) == 58.0

        diags = apply_persisted_values(registry, spec)

        # Wrappers issued earlier now see persisted values.
        assert str(theme.primary) == "#abcdef"
        assert float(theme.hero) == 64.0
        assert diags == []


def test_apply_persisted_values_when_file_missing(tmp_path: Path) -> None:
    spec = tmp_path / "build.py"
    registry = TweakRegistry()
    with tweak_context(registry):
        theme = tweaks.group("theme", primary=tweaks.color(default="#111111"))
        diags = apply_persisted_values(registry, spec)
    assert diags == []
    assert str(theme.primary) == "#111111"


def test_apply_persisted_values_drops_invalid_values(tmp_path: Path) -> None:
    spec = tmp_path / "build.py"
    (tmp_path / "theme.toml").write_text(
        '[theme]\nhero = "large"\n', encoding="utf-8"
    )
    registry = TweakRegistry()
    with tweak_context(registry):
        theme = tweaks.group("theme", hero=tweaks.size_pt(default=58, min=32, max=76))
        diags = apply_persisted_values(registry, spec)
        # Default still in effect.
        assert float(theme.hero) == 58.0
    assert len(diags) == 1
    assert diags[0].severity == "error"


# ---------------------------------------------------------------------------
# write_persisted_values
# ---------------------------------------------------------------------------


def test_write_produces_deterministic_sorted_output(tmp_path: Path) -> None:
    registry = _make_registry()
    out = tmp_path / "theme.toml"
    write_persisted_values(out, registry)
    text = out.read_text(encoding="utf-8")
    assert text == textwrap.dedent(
        """
        [layout]
        density = "comfortable"
        gap_mm = 8.0

        [theme]
        hero = 58.0
        primary = "#111111"
        """
    ).lstrip()


def test_write_is_idempotent(tmp_path: Path) -> None:
    registry = _make_registry()
    out = tmp_path / "theme.toml"
    write_persisted_values(out, registry)
    first = out.read_bytes()
    write_persisted_values(out, registry)
    second = out.read_bytes()
    assert first == second


def test_write_round_trips_through_load(tmp_path: Path) -> None:
    registry = _make_registry()
    out = tmp_path / "theme.toml"
    write_persisted_values(out, registry)
    raw = load_persisted_values(out)
    assert raw == {
        "layout": {"density": "comfortable", "gap_mm": 8.0},
        "theme": {"hero": 58.0, "primary": "#111111"},
    }


def test_write_reflects_applied_values(tmp_path: Path) -> None:
    registry = _make_registry()
    registry.apply_values({"theme.primary": "#abcdef", "theme.hero": 64.0})
    out = tmp_path / "theme.toml"
    write_persisted_values(out, registry)
    raw = load_persisted_values(out)
    assert raw is not None
    assert raw["theme"]["primary"] == "#abcdef"
    assert raw["theme"]["hero"] == 64.0


def test_write_escapes_strings(tmp_path: Path) -> None:
    registry = TweakRegistry()
    with tweak_context(registry):
        tweaks.group(
            "theme",
            font=tweaks.font_choice(
                default='Inter "Display"', options=('Inter "Display"', "Body")
            ),
        )
    out = tmp_path / "theme.toml"
    write_persisted_values(out, registry)
    raw = load_persisted_values(out)
    assert raw is not None
    assert raw["theme"]["font"] == 'Inter "Display"'


def test_write_rejects_unsupported_value_types(tmp_path: Path) -> None:
    """Reserved branch: no helper produces dict/object values today, but the
    formatter must refuse rather than silently coerce something it does not
    understand."""

    from folio.core.dsl.tweak_values import _format_value

    with pytest.raises(TypeError):
        _format_value({"unsupported": "object"})


def test_write_handles_empty_registry(tmp_path: Path) -> None:
    registry = TweakRegistry()
    out = tmp_path / "theme.toml"
    write_persisted_values(out, registry)
    assert out.read_text(encoding="utf-8") == ""
