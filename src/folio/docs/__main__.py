"""Module entrypoint: `python -m folio.docs` forwards to `folio.docs.generate`."""

from __future__ import annotations

import sys

from folio.docs.generate import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
