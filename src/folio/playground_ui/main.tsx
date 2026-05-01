// Entry point for the Folio playground UI. Vite resolves this file from
// the source ``index.html`` and rewrites it into ``playground.js`` in the
// packaged static-asset directory at build time.

import { render } from "solid-js/web";

import { App } from "./App";
import { createPlaygroundStore } from "./state";

const root = document.getElementById("root");
if (!root) throw new Error("missing #root container");

const store = createPlaygroundStore();
render(() => <App store={store} />, root);
void store.loadState();
