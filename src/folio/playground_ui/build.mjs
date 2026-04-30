import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import * as esbuild from "esbuild";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../../..");
const outDir = resolve(repoRoot, "src/folio/services/playground_assets");

const sourceFiles = [
  "src/folio/playground_ui/index.html",
  "src/folio/playground_ui/main.ts",
  "src/folio/playground_ui/styles.css",
  "src/folio/playground_ui/README.md",
  "src/folio/playground_ui/build.mjs",
  "package.json",
  "package-lock.json",
];

await mkdir(outDir, { recursive: true });

await esbuild.build({
  entryPoints: [resolve(repoRoot, "src/folio/playground_ui/main.ts")],
  outfile: resolve(outDir, "playground.js"),
  bundle: true,
  format: "esm",
  target: "es2020",
  sourcemap: false,
  minify: false,
});

await writeFile(
  resolve(outDir, "index.html"),
  await readFile(resolve(repoRoot, "src/folio/playground_ui/index.html"), "utf8"),
  "utf8",
);
await writeFile(
  resolve(outDir, "playground.css"),
  await readFile(resolve(repoRoot, "src/folio/playground_ui/styles.css"), "utf8"),
  "utf8",
);
await writeFile(resolve(outDir, "__init__.py"), '"""Packaged static assets for `folio dev`."""\n', "utf8");

const manifest = {
  build: "npm run build:playground",
  sourceHashes: {},
};
for (const file of sourceFiles) {
  const body = await readFile(resolve(repoRoot, file));
  manifest.sourceHashes[file] = createHash("sha256").update(body).digest("hex");
}
await writeFile(resolve(outDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
