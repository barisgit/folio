import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { build as viteBuild } from "vite";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../../..");
const outDir = resolve(repoRoot, "src/folio/services/playground_assets");

// Files whose hashes are recorded in the manifest. The Python tests use
// the manifest schema to verify the bundle is fresh; the file list is no
// longer pinned by tests, so adding/removing entries here is safe.
const sourceFiles = [
  "src/folio/playground_ui/index.html",
  "src/folio/playground_ui/main.tsx",
  "src/folio/playground_ui/App.tsx",
  "src/folio/playground_ui/state.ts",
  "src/folio/playground_ui/api.ts",
  "src/folio/playground_ui/api.generated.ts",
  "src/folio/playground_ui/styles.css",
  "src/folio/playground_ui/uno.config.ts",
  "src/folio/playground_ui/vite.config.ts",
  "src/folio/playground_ui/README.md",
  "src/folio/playground_ui/build.mjs",
  "src/folio/_dev/gen_playground_types.py",
  "package.json",
  "bun.lock",
];

await mkdir(outDir, { recursive: true });

// Vite reads ``vite.config.ts`` from the playground_ui directory; it
// emits ``index.html``, ``playground.js`` and ``playground.css`` directly
// into the Python static-asset directory.
await viteBuild({
  configFile: resolve(here, "vite.config.ts"),
  logLevel: "warn",
});

// Vite output rewrites the script tag to ``/assets/playground.js``;
// strip the leading slash off the css link too. The Python static
// handler serves any path under ``/assets/`` from this directory.
const indexPath = resolve(outDir, "index.html");
let indexHtml = await readFile(indexPath, "utf8");
// Vite emits absolute paths under ``base`` (``/assets/...``), which is
// exactly what the runtime server expects. No rewrite needed.
await writeFile(indexPath, indexHtml, "utf8");

await writeFile(
  resolve(outDir, "__init__.py"),
  '"""Packaged static assets for `folio dev`."""\n',
  "utf8",
);

const manifest = {
  build: "bun run build:playground",
  sourceHashes: {},
};
for (const file of sourceFiles) {
  const body = await readFile(resolve(repoRoot, file));
  manifest.sourceHashes[file] = createHash("sha256").update(body).digest("hex");
}
await writeFile(
  resolve(outDir, "manifest.json"),
  `${JSON.stringify(manifest, null, 2)}\n`,
  "utf8",
);
