import { defineConfig } from "vite";
import solidPlugin from "vite-plugin-solid";
import { resolve } from "node:path";

// Output goes straight into the Python package's static-asset directory
// so the stdlib HTTP server can serve it without any extra copy step.
//
// File names are deterministic (no content hash) because Python's
// asset-resource lookup and the manifest source-hash check expect the
// exact paths ``playground.js`` / ``playground.css`` /  ``index.html``.
const here = __dirname;
const repoRoot = resolve(here, "../../..");
const outDir = resolve(repoRoot, "src/folio/services/playground_assets");

export default defineConfig({
  root: here,
  base: "/assets/",
  plugins: [solidPlugin()],
  build: {
    outDir,
    emptyOutDir: false,
    sourcemap: false,
    minify: true,
    target: "es2020",
    rollupOptions: {
      input: resolve(here, "index.html"),
      output: {
        entryFileNames: "playground.js",
        assetFileNames: (info) => {
          if (info.name && info.name.endsWith(".css")) return "playground.css";
          return "[name][extname]";
        },
        chunkFileNames: "[name].js",
      },
    },
  },
});
