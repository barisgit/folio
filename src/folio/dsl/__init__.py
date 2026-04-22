from __future__ import annotations

from . import builtins as _builtins
from . import tokens
from .model import Asset, DefNode, Document, Element, ElementKind, Markup, Page, TextSpan
from .styles import TextStyle

Block = _builtins.Block
block = _builtins.block
circle = _builtins.circle
clip_path = _builtins.clip_path
component_transfer = _builtins.component_transfer
filter_ = _builtins.filter_
func_a = _builtins.func_a
gaussian_blur = _builtins.gaussian_blur
group = _builtins.group
image = _builtins.image
line = _builtins.line
linear_gradient = _builtins.linear_gradient
markup = _builtins.markup
merge = _builtins.merge
merge_node = _builtins.merge_node
multiline = _builtins.multiline
offset = _builtins.offset
page = _builtins.page
path = _builtins.path
radial_gradient = _builtins.radial_gradient
rect = _builtins.rect
render = _builtins.render
rule = _builtins.rule
span = _builtins.tspan
stop = _builtins.stop
svg_node = _builtins.svg_node
text = _builtins.text
triangle = _builtins.triangle
tspan = _builtins.tspan

__all__ = [
    "Asset",
    "Block",
    "DefNode",
    "Document",
    "Element",
    "ElementKind",
    "Markup",
    "Page",
    "TextSpan",
    "TextStyle",
    "block",
    "circle",
    "clip_path",
    "component_transfer",
    "filter_",
    "func_a",
    "gaussian_blur",
    "group",
    "image",
    "line",
    "linear_gradient",
    "markup",
    "merge",
    "merge_node",
    "multiline",
    "offset",
    "page",
    "path",
    "radial_gradient",
    "rect",
    "render",
    "rule",
    "span",
    "stop",
    "svg_node",
    "text",
    "tokens",
    "triangle",
    "tspan",
]
