"""Compatibility shim for older imports.

Prefer `folio.dsl.renderer` for renderer/build internals.
Use `from folio.dsl import render` for the public document builder.
"""

from __future__ import annotations

from folio.dsl.renderer import *  # noqa: F403
