from __future__ import annotations

import pytest

from folio.core.dsl.styles import TextStyle
from folio.core.dsl.tweaks import (
    TweakDeclaration,
    TweakGroup,
    TweakRegistry,
    TweakValue,
    tweak_context,
)
from folio.dsl import tweaks


# ---------------------------------------------------------------------------
# Registry / context
# ---------------------------------------------------------------------------


def test_helpers_outside_context_raise():
    with pytest.raises(RuntimeError, match="tweak_context"):
        tweaks.group("theme", primary=tweaks.color(default="#d9a64b"))


def test_registry_isolation_across_contexts():
    with tweak_context() as r1:
        tweaks.group("theme", primary=tweaks.color(default="#111111"))
        assert "theme.primary" in r1.declarations
    with tweak_context() as r2:
        tweaks.group("theme", primary=tweaks.color(default="#222222"))
        assert list(r2.declarations) == ["theme.primary"]
        # values from r1 must not leak
        assert r2.resolved("theme.primary") == "#222222"


def test_nested_contexts_are_independent():
    with tweak_context() as outer:
        tweaks.group("outer", a=tweaks.color(default="#aaaaaa"))
        with tweak_context() as inner:
            tweaks.group("inner", b=tweaks.color(default="#bbbbbb"))
            assert "outer.a" not in inner.declarations
            assert "inner.b" in inner.declarations
        # outer regains active status; can still register
        tweaks.group("outer2", c=tweaks.color(default="#cccccc"))
        assert {"outer.a", "outer2.c"} <= outer.declarations.keys()


def test_duplicate_dotted_key_rejected():
    with tweak_context():
        tweaks.group("theme", primary=tweaks.color(default="#111111"))
        with pytest.raises(ValueError, match="duplicate tweak key"):
            tweaks.group("theme", primary=tweaks.color(default="#222222"))


def test_apply_values_resolves_persisted_value():
    with tweak_context() as registry:
        registry.apply_values({"theme.primary": "#abcdef"})
        theme = tweaks.group("theme", primary=tweaks.color(default="#111111"))
        assert str(theme.primary) == "#abcdef"
        assert registry.resolved("theme.primary") == "#abcdef"


def test_registry_snapshot_is_frozen():
    with tweak_context() as registry:
        tweaks.group("theme", primary=tweaks.color(default="#111111"))
    snap = registry.snapshot()
    assert isinstance(snap.declarations, tuple)
    assert isinstance(snap.diagnostics, tuple)
    assert snap.declarations[0].key == "theme.primary"


# ---------------------------------------------------------------------------
# Helper validation (declaration time)
# ---------------------------------------------------------------------------


def test_color_default_required():
    with tweak_context():
        with pytest.raises(TypeError, match="default"):
            tweaks.color()  # type: ignore[call-arg]


def test_color_normalizes_hex():
    with tweak_context() as registry:
        tweaks.group("theme", primary=tweaks.color(default="#D9A64B"))
        assert registry.resolved("theme.primary") == "#d9a64b"


def test_color_rejects_garbage():
    with tweak_context():
        with pytest.raises(ValueError, match="recognised CSS color"):
            tweaks.group("theme", x=tweaks.color(default="not-a-color-123"))


@pytest.mark.parametrize(
    "helper,kwargs",
    [
        ("size_pt", {}),
        ("size_mm", {}),
        ("opacity", {}),
        ("letter_spacing", {}),
        ("stroke_width", {}),
    ],
)
def test_numeric_helpers_default_required(helper, kwargs):
    fn = getattr(tweaks, helper)
    with tweak_context():
        with pytest.raises(TypeError, match="default"):
            fn(**kwargs)


def test_numeric_helper_rejects_string_default():
    with tweak_context():
        with pytest.raises(TypeError, match="must be a number"):
            tweaks.size_pt(default="big")  # type: ignore[arg-type]


def test_numeric_range_enforced_on_default():
    with tweak_context():
        with pytest.raises(ValueError, match="below min"):
            tweaks.size_pt(default=10, min=20, max=40)
        with pytest.raises(ValueError, match="above max"):
            tweaks.size_pt(default=99, min=20, max=40)


def test_choice_requires_options_and_default_in_options():
    with tweak_context():
        with pytest.raises(TypeError, match="options"):
            tweaks.choice(default="a", options=())  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="not in options"):
            tweaks.choice(default="z", options=("a", "b"))


def test_choice_options_unique():
    with tweak_context():
        with pytest.raises(ValueError, match="duplicates"):
            tweaks.choice(default="a", options=("a", "a", "b"))


def test_unsafe_live_override_rejected_for_rebuild_only_class():
    with tweak_context():
        with pytest.raises(ValueError, match="does not support live mode"):
            tweaks.size_mm(default=8, mode="live")
        with pytest.raises(ValueError, match="does not support live mode"):
            tweaks.choice(default="a", options=("a", "b"), mode="live")


def test_invalid_mode_string_rejected():
    with tweak_context():
        with pytest.raises(ValueError, match="must be 'live' or 'rebuild'"):
            tweaks.color(default="#000000", mode="async")


def test_group_name_must_be_identifier():
    with tweak_context():
        with pytest.raises(ValueError, match="alphanumeric"):
            tweaks.group("with-dash", x=tweaks.color(default="#000000"))


def test_group_requires_at_least_one_member():
    with tweak_context():
        with pytest.raises(TypeError, match="at least one"):
            tweaks.group("theme")


def test_group_member_must_be_helper_result():
    with tweak_context():
        with pytest.raises(TypeError, match="result of a tweak helper"):
            tweaks.group("theme", primary="#111111")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TweakValue behavior
# ---------------------------------------------------------------------------


def test_tweak_value_primitive_coercion():
    with tweak_context() as registry:
        registry.apply_values({"theme.size": 58})
        theme = tweaks.group("theme", size=tweaks.size_pt(default=42))
        v = theme.size
        assert isinstance(v, TweakValue)
        assert float(v) == 58.0
        assert int(v) == 58
        assert str(v) == "58"
        assert bool(v) is True


def test_tweak_value_color_str_returns_color():
    with tweak_context():
        theme = tweaks.group("theme", primary=tweaks.color(default="#d9a64b"))
        assert str(theme.primary) == "#d9a64b"


def test_tweak_value_css_var_shape():
    with tweak_context():
        theme = tweaks.group(
            "theme",
            primary=tweaks.color(default="#111111"),
            hero_size_pt=tweaks.size_pt(default=58),
        )
        assert theme.primary.css_var == "--folio-tweak-theme-primary"
        assert theme.hero_size_pt.css_var == "--folio-tweak-theme-hero-size-pt"


def test_tweak_value_arithmetic_returns_primitive():
    with tweak_context():
        theme = tweaks.group("theme", size=tweaks.size_pt(default=58))
        derived = theme.size + 4
        # derived value is a plain primitive, not a TweakValue
        assert not isinstance(derived, TweakValue)
        assert derived == 62.0
        assert isinstance(derived, float)


def test_tweak_value_equality_against_primitive():
    with tweak_context():
        theme = tweaks.group("theme", size=tweaks.size_pt(default=58))
        assert theme.size == 58
        assert theme.size != 59


def test_tweak_value_equality_against_tweak_value():
    with tweak_context() as registry:
        a = tweaks.group("a", x=tweaks.size_pt(default=10))
        # Same key + same resolved value → equal; different key → unequal
        assert a.x == a.x
        registry.declarations.clear()  # clear and re-register fresh keys for second group
        b = tweaks.group("a", x=tweaks.size_pt(default=10))
        assert a.x == b.x


# ---------------------------------------------------------------------------
# Group proxy
# ---------------------------------------------------------------------------


def test_group_returns_tweak_group_with_attribute_access():
    with tweak_context():
        theme = tweaks.group(
            "theme",
            primary=tweaks.color(default="#111111"),
            hero=tweaks.size_pt(default=58),
        )
        assert isinstance(theme, TweakGroup)
        assert isinstance(theme.primary, TweakValue)
        assert isinstance(theme.hero, TweakValue)
        assert theme.primary.key == "theme.primary"
        assert theme.hero.key == "theme.hero"


def test_group_unknown_member_raises_attribute_error():
    with tweak_context():
        theme = tweaks.group("theme", primary=tweaks.color(default="#111111"))
        with pytest.raises(AttributeError, match="missing|no member"):
            _ = theme.does_not_exist


# ---------------------------------------------------------------------------
# TextStyle preserves TweakValue (live-eligible fields)
# ---------------------------------------------------------------------------


def test_text_style_preserves_tweak_value_for_font_size_pt():
    with tweak_context():
        theme = tweaks.group("theme", hero=tweaks.size_pt(default=58))
        style = TextStyle(font_size_pt=theme.hero)
        assert isinstance(style.font_size_pt, TweakValue)
        assert style.font_size_pt is theme.hero


def test_text_style_preserves_tweak_value_for_fill():
    with tweak_context():
        theme = tweaks.group("theme", primary=tweaks.color(default="#d9a64b"))
        style = TextStyle(fill=theme.primary)
        assert isinstance(style.fill, TweakValue)
        assert style.fill is theme.primary


def test_text_style_preserves_tweak_value_for_letter_spacing_and_fill_opacity():
    with tweak_context():
        theme = tweaks.group(
            "theme",
            ls=tweaks.letter_spacing(default=-2.0),
            op=tweaks.opacity(default=0.85),
        )
        style = TextStyle(letter_spacing=theme.ls, fill_opacity=theme.op)
        assert isinstance(style.letter_spacing, TweakValue)
        assert isinstance(style.fill_opacity, TweakValue)


def test_text_style_text_attrs_round_trips_tweak_value():
    """text_attrs() must return the wrapper as-is so the renderer can decide
    whether to unwrap it (build mode) or emit a CSS variable later."""

    with tweak_context():
        theme = tweaks.group("theme", hero=tweaks.size_pt(default=58))
        style = TextStyle(font_size_pt=theme.hero, fill="#fff")
        attrs = style.text_attrs()
        assert isinstance(attrs["size_pt"], TweakValue)
        assert attrs["fill"] == "#fff"


def test_text_style_derived_expression_loses_metadata():
    """Coercing through float() in the spec drops live metadata, as
    documented in the design."""

    with tweak_context():
        theme = tweaks.group("theme", hero=tweaks.size_pt(default=58))
        derived = float(theme.hero) + 4
        style = TextStyle(font_size_pt=derived)
        assert not isinstance(style.font_size_pt, TweakValue)
        assert style.font_size_pt == 62.0


# ---------------------------------------------------------------------------
# Re-export surface
# ---------------------------------------------------------------------------


def test_tweaks_namespace_via_folio_dsl():
    import folio.dsl as dsl

    assert hasattr(dsl, "tweaks")
    assert dsl.tweaks.color is tweaks.color


def test_decl_records_constraints():
    with tweak_context() as registry:
        tweaks.group(
            "theme",
            hero=tweaks.size_pt(default=58, min=32, max=76, label="Hero size"),
        )
        decl: TweakDeclaration = registry.declarations["theme.hero"]
        assert decl.kind == "size_pt"
        assert decl.min == 32
        assert decl.max == 76
        assert decl.label == "Hero size"
        assert decl.mode == "live"
        assert decl.group == "theme"
        assert decl.name == "hero"


def test_isolated_registry_returned_by_context_manager():
    reg = TweakRegistry()
    with tweak_context(reg) as bound:
        assert bound is reg
        tweaks.group("theme", primary=tweaks.color(default="#111111"))
    assert "theme.primary" in reg.declarations
