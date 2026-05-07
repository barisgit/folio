// AUTO-GENERATED - do not edit. Run `bun run build:playground` to regenerate this file.
// Source: src/folio/_dev/gen_playground_types.py

export interface Diagnostic {
  severity: string;
  key: null | string;
  message: string;
}

export interface PlaygroundPage {
  pageNumber: number;
  pageId: string;
  filename: string;
  svg: string;
  documentId: string;
  documentLabel: string;
  widthMm: number;
  heightMm: number;
}

export interface PlaygroundTweak {
  key: string;
  group: string;
  name: string;
  kind: string;
  mode: string;
  value: unknown;
  default: unknown;
  cssVar: string;
  label: null | string;
  min: null | number;
  max: null | number;
  options: null | string[];
  diverged: boolean;
}

export interface PlaygroundState {
  specPath: string;
  valuesPath: string;
  pages: PlaygroundPage[];
  tweaks: PlaygroundTweak[];
  values: Record<string, unknown>;
  diagnostics: Diagnostic[];
}

export interface TweakUpdateRequest {
  updates?: Record<string, unknown> | null;
  key?: null | string;
  value?: unknown;
}

export interface ResetTweakRequest {
  scope?: "all" | "group" | "tweak";
  key?: null | string;
  group?: null | string;
}
