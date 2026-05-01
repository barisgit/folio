"""Maintainer-only development helpers.

This package is excluded from built wheels and sdists; nothing here is
loaded by the runtime ``folio`` package. It exists to share Python
codegen utilities (e.g. Pydantic model -> TypeScript types) used by the
in-repo ``bun run build:playground`` workflow.
"""
