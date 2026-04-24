"""Parse the Google-style docstrings used across the public DSL.

The format is intentionally small so the DSL surface stays readable:

    One-line summary.

    Optional longer description that can span multiple paragraphs. Paragraphs
    before the first section marker form the long-form description.

    Args:
        name: Description of the parameter.
        other: Another parameter.

    Returns:
        Element: What the symbol returns.

    Example:
        # Optional caption as the first comment line.
        rect(None, 0, 0, 10, 10)

    Tags: layout, shape

A symbol may carry more than one `Example:` section. Every block gets
parsed into a structured :class:`Example` with a caption derived from an
optional leading `# ...` comment inside the block.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from textwrap import dedent

from folio.services.docs.schema import Example

_SECTION_RE = re.compile(
    r"^(Args|Arguments|Parameters|Returns|Return|Example|Examples|Tags|Raises)\s*:\s*(?P<tail>.*)$"
)
_ARG_LINE_RE = re.compile(r"^(?P<name>\*{0,2}\w+)(?:\s*\(.*\))?\s*:\s*(?P<doc>.*)$")
_TAG_SEP_RE = re.compile(r"[,\s]+")


@dataclass(frozen=True, slots=True)
class ParsedDoc:
    summary: str
    description: str
    params: dict[str, str]
    returns_doc: str
    examples: tuple[Example, ...]
    tags: tuple[str, ...]


def parse_docstring(raw: str | None) -> ParsedDoc | None:
    """Return a :class:`ParsedDoc` or None when the docstring is empty."""
    if raw is None:
        return None
    docstring = dedent(raw).strip()
    if not docstring:
        return None
    lines = docstring.splitlines()
    summary_lines: list[str] = []
    cursor = 0
    while cursor < len(lines) and lines[cursor].strip():
        summary_lines.append(lines[cursor].strip())
        cursor += 1
    summary = " ".join(summary_lines).strip()

    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1

    sections, description = _split_sections(lines[cursor:])

    params: dict[str, str] = {}
    for block_name in ("Args", "Arguments", "Parameters"):
        for body in sections.get(block_name, ()):
            params.update(_parse_args_block(body))

    returns_doc = ""
    for block_name in ("Returns", "Return"):
        for body in sections.get(block_name, ()):
            text = _join_body(body)
            if text:
                returns_doc = text
                break
        if returns_doc:
            break

    examples: list[Example] = []
    for block_name in ("Example", "Examples"):
        for body in sections.get(block_name, ()):
            examples.extend(_parse_example_block(body))

    tags: tuple[str, ...] = ()
    for body in sections.get("Tags", ()):
        joined = _join_body(body)
        if joined:
            tags = tuple(tag for tag in _TAG_SEP_RE.split(joined) if tag)
            break

    return ParsedDoc(
        summary=summary,
        description=description,
        params=params,
        returns_doc=returns_doc,
        examples=tuple(examples),
        tags=tags,
    )


def _split_sections(lines: list[str]) -> tuple[dict[str, list[list[str]]], str]:
    description_lines: list[str] = []
    sections: dict[str, list[list[str]]] = {}
    current: tuple[str, list[str]] | None = None
    before_first_section = True

    for raw_line in lines:
        stripped = raw_line.strip()
        match = _SECTION_RE.match(stripped)
        if match:
            if current is not None:
                sections.setdefault(current[0], []).append(current[1])
            tail = match.group("tail").strip()
            current = (_canonical_section(match.group(1)), [tail] if tail else [])
            before_first_section = False
            continue
        if current is None:
            if before_first_section:
                description_lines.append(raw_line)
            continue
        current[1].append(raw_line)

    if current is not None:
        sections.setdefault(current[0], []).append(current[1])

    description = dedent("\n".join(description_lines)).strip()
    return sections, description


def _canonical_section(name: str) -> str:
    if name == "Arguments" or name == "Parameters":
        return "Args"
    if name == "Return":
        return "Returns"
    if name == "Examples":
        return "Example"
    return name


def _parse_args_block(body: list[str]) -> dict[str, str]:
    text = dedent("\n".join(body)).rstrip()
    params: dict[str, str] = {}
    current_name: str | None = None
    current_doc: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            if current_name is not None:
                current_doc.append("")
            continue
        match = _ARG_LINE_RE.match(line)
        if match and (line[0] != " " or current_name is None):
            if current_name is not None:
                params[current_name] = _collapse_paragraph(current_doc)
            current_name = match.group("name")
            current_doc = [match.group("doc").strip()]
        elif current_name is not None:
            current_doc.append(line.strip())
    if current_name is not None:
        params[current_name] = _collapse_paragraph(current_doc)
    return params


def _parse_example_block(body: list[str]) -> list[Example]:
    block = dedent("\n".join(body)).rstrip("\n")
    if not block.strip():
        return []
    stripped_lines = block.splitlines()
    caption: str | None = None
    if stripped_lines and stripped_lines[0].lstrip().startswith("#"):
        caption = stripped_lines[0].lstrip().lstrip("#").strip() or None
        stripped_lines = stripped_lines[1:]
        while stripped_lines and not stripped_lines[0].strip():
            stripped_lines = stripped_lines[1:]
    code = "\n".join(stripped_lines).rstrip()
    if not code.strip():
        return []
    return [Example(code=code, caption=caption, setup=None)]


def _join_body(body: list[str]) -> str:
    return dedent("\n".join(body)).strip()


def _collapse_paragraph(lines: list[str]) -> str:
    paragraph: list[str] = []
    for fragment in lines:
        if fragment:
            paragraph.append(fragment)
    return " ".join(paragraph).strip()
