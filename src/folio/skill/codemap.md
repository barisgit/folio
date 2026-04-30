# `folio.skill` — Bundled Claude Code Skill

## Responsibility

Packages Folio's Claude Code skill as **file assets** that can be installed into a Claude Code skills directory. The package itself contains only **file location utilities**; the skill workflow documentation lives in `SKILL.md`. This enables the `folio skill install` command to copy bundled skill files into the agent's skills directory.

## Design

### Architecture
- **Pure asset management module** — no business logic
- **Two public functions** expose skill files for discovery and installation
- **No runtime imports** of skill assets (SKILL.md is text, not Python)

### File Structure
```
folio/skill/
├── __init__.py    # Asset management functions
├── SKILL.md       # Skill workflow documentation
└── __pycache__/   # Python bytecode (excluded from assets)
```

### Abstractions

| Function | Signature | Returns |
|----------|-----------|---------|
| `skill_root()` | `() -> Path` | Absolute path to skill directory |
| `skill_assets()` | `() -> list[Path]` | All skill files except `__init__.py` and bytecode |

### Exported API
```python
from folio.skill import skill_assets, skill_root
```

## Flow

```
folio skill install
    │
    ├── skill_root() → locate bundled skill directory
    │
    └── skill_assets() → enumerate files to copy
            │
            ├── SKILL.md           (required)
            ├── __init__.py        (excluded)
            └── __pycache__/*      (excluded)
```

## Integration

### Dependencies
- **`pathlib.Path`** — file system path handling
- **Standard library only** — no external dependencies

### Consumers
- **`folio.cli`** — `skill install` command reads assets for copying
- **Claude Code agent** — reads `SKILL.md` for workflow guidance
- **Installation scripts** — copy skill files to `.agents/skills/folio/` or `.claude/skills/folio/`

### Skill Content (SKILL.md)
The bundled skill defines the canonical Folio workflow:

1. **`folio check`** — validate → examples → lint → typecheck
2. **`folio build`** — render spec to SVG/PDF/IDML artifacts
3. **`folio rasterize`** — convert SVGs to PNGs for preview
4. **`folio reconcile`** — apply SVG edits back to spec
5. **`folio docs`** — lookup DSL symbols and signatures

### Installation Target
- Default: `.agents/skills/folio/`
- Claude Code convention: `.claude/skills/folio/` (symlink recommended)
- Symlink command: `ln -s .agents/skills/folio .claude/skills/folio`

## Constraints

- `skill_assets()` filters out `__init__.py` and `__pycache__/` by name
- Returns `list[Path]` sorted alphabetically for deterministic output
- Files are read-only assets; no write operations from this module
