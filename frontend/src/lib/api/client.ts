import createClient from "openapi-fetch";
import type { paths } from "./schema";

/** Typed client for the backend API. Cookies carry the session; the server checks fetch metadata for CSRF. */
// The page's own origin: the API lives next to the app, and absolute URLs also work where Request needs them.
const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;

export const api = createClient<paths>({
  baseUrl: origin,
  credentials: "same-origin",
  // Resolve fetch at call time so a test can replace it after this module loaded.
  fetch: (request) => globalThis.fetch(request),
});

interface FastApiError {
  detail?: string | { msg: string; loc?: (string | number)[] }[];
}

/** Turn a FastAPI error body into one sentence for people. */
export function errorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as FastApiError).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0 && detail[0]) {
      const first = detail[0];
      const field = first.loc?.filter((part) => typeof part === "string" && part !== "body").join(".");
      return field ? `${field}: ${first.msg}` : first.msg;
    }
  }
  return fallback;
}
