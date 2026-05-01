// Thin fetch wrappers around the Folio playground HTTP API.

import type { PlaygroundState } from "./api.generated";

export const API_STATE = "/api/state";
export const API_TWEAKS = "/api/tweaks";

export async function fetchState(): Promise<PlaygroundState> {
  const response = await fetch(API_STATE);
  const payload = await response.json();
  if (!response.ok) {
    throw Object.assign(new Error("failed to load state"), { payload });
  }
  return payload as PlaygroundState;
}

export async function patchTweakValue(
  key: string,
  value: unknown,
): Promise<PlaygroundState> {
  const response = await fetch(API_TWEAKS, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, value }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw Object.assign(new Error("update rejected"), { payload });
  }
  return payload as PlaygroundState;
}
