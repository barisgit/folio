// UnoCSS configuration for the Folio playground UI.
//
// Phase 1 of the migration: UnoCSS coexists with the legacy
// ``styles.css``. Custom theme tokens reference the CSS variables
// defined in ``styles.css`` so utilities like ``bg-accent`` resolve to
// the same values as ``var(--accent)``. This avoids duplicating the
// palette while later phases incrementally replace hand-rolled rules
// with utilities and shortcuts.

import { defineConfig, presetIcons, presetWind4 } from "unocss";

export default defineConfig({
  presets: [
    presetWind4(),
    // Inline icons via ``i-lucide-*`` class names. ``cdn: false`` keeps
    // the icon SVGs bundled at build time so the playground works
    // offline.
    presetIcons({ scale: 1.0, cdn: false }),
  ],
  theme: {
    colors: {
      accent: "var(--accent)",
      "accent-hi": "var(--accent-hi)",
      "accent-soft": "var(--accent-soft)",
      "accent-glow": "var(--accent-glow)",
      "bg-canvas": "var(--bg-canvas)",
      "bg-surface": "var(--bg-surface)",
      "bg-surface-2": "var(--bg-surface-2)",
      "bg-elevated": "var(--bg-elevated)",
      border: "var(--border)",
      "border-strong": "var(--border-strong)",
      "border-active": "var(--border-active)",
      fg: "var(--fg)",
      "fg-strong": "var(--fg-strong)",
      "fg-muted": "var(--fg-muted)",
      "fg-dim": "var(--fg-dim)",
      ok: "var(--ok)",
      warn: "var(--warn)",
      err: "var(--err)",
    },
    fontFamily: {
      sans: "var(--font-sans)",
      mono: "var(--font-mono)",
      display: "var(--font-display)",
    },
  },
  // Phase 1 deliberately ships zero shortcuts. SelectControl uses
  // Kobalte's own primitives plus the existing ``.tweak-select-*``
  // classes from ``styles.css``; the only new utility consumed is the
  // ``i-lucide-rotate-ccw`` icon. Add shortcuts as later phases convert
  // chrome that genuinely repeats.
});
