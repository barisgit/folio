"""Folio core DSL — element factories, composition, and tokens."""

from __future__ import annotations

from folio.core.dsl import builtins as _builtins
from folio.core.dsl import tokens, tweaks
from folio.core.dsl.charts import ChartHandle, chart
from folio.core.dsl.styles import TextStyle
from folio.core.layout.helpers import cols, flow_cols, grid
from folio.core.model import (
    Asset,
    DefNode,
    Document,
    DocumentCollection,
    Element,
    ElementKind,
    ExportFormat,
    ExportPreset,
    ExportScope,
    Markup,
    Page,
    TextMetrics,
    TextSpan,
)

Block = _builtins.Block
block = _builtins.block
circle = _builtins.circle
clip_path = _builtins.clip_path
collection = _builtins.collection
component_transfer = _builtins.component_transfer
document = _builtins.document
drop_shadow = _builtins.drop_shadow
ellipse = _builtins.ellipse
filter_ = _builtins.filter_
grain = _builtins.grain
func_a = _builtins.func_a
gaussian_blur = _builtins.gaussian_blur
group = _builtins.group
idml = _builtins.idml
image = _builtins.image
line = _builtins.line
linear_gradient = _builtins.linear_gradient
linear_gradient_stops = _builtins.linear_gradient_stops
markup = _builtins.markup
mask = _builtins.mask
merge = _builtins.merge
merge_node = _builtins.merge_node
measure_text = _builtins.measure_text
measure_wrapped_text = _builtins.measure_wrapped_text
multiline = _builtins.multiline
offset = _builtins.offset
page = _builtins.page
path = _builtins.path
path_builder = _builtins.path_builder
pdf = _builtins.pdf
png = _builtins.png
polygon = _builtins.polygon
polyline = _builtins.polyline
qr = _builtins.qr
transform_builder = _builtins.transform_builder
radial_gradient = _builtins.radial_gradient
rect = _builtins.rect
render = _builtins.render
rule = _builtins.rule
span = _builtins.tspan
stop = _builtins.stop
svg = _builtins.svg
svg_node = _builtins.svg_node
text = _builtins.text
triangle = _builtins.triangle
tspan = _builtins.tspan
wrapped_text = _builtins.wrapped_text
PathBuilder = _builtins.PathBuilder
TextLayoutWarning = _builtins.TextLayoutWarning
TransformBuilder = _builtins.TransformBuilder

__all__ = [
    "Asset",
    "Block",
    "ChartHandle",
    "DefNode",
    "Document",
    "DocumentCollection",
    "Element",
    "ElementKind",
    "ExportFormat",
    "ExportPreset",
    "ExportScope",
    "Markup",
    "Page",
    "PathBuilder",
    "TextLayoutWarning",
    "TextMetrics",
    "TextSpan",
    "TextStyle",
    "TransformBuilder",
    "block",
    "chart",
    "circle",
    "clip_path",
    "collection",
    "cols",
    "component_transfer",
    "document",
    "drop_shadow",
    "ellipse",
    "filter_",
    "flow_cols",
    "func_a",
    "gaussian_blur",
    "grain",
    "grid",
    "group",
    "idml",
    "image",
    "line",
    "linear_gradient",
    "linear_gradient_stops",
    "markup",
    "mask",
    "measure_text",
    "measure_wrapped_text",
    "merge",
    "merge_node",
    "multiline",
    "offset",
    "page",
    "path",
    "path_builder",
    "pdf",
    "png",
    "polygon",
    "polyline",
    "qr",
    "radial_gradient",
    "rect",
    "render",
    "rule",
    "span",
    "stop",
    "svg",
    "svg_node",
    "text",
    "tokens",
    "transform_builder",
    "triangle",
    "tspan",
    "tweaks",
    "wrapped_text",
]
