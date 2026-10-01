/** Same-origin `/api` when the CRA backend URL is missing, blank, or the
 *  literal string "undefined" (empty `REACT_APP_BACKEND_URL=` in the Windows
 *  installer build). Never emit `/undefined/api` — that 405s license POST.
 */
export function resolveApiBase(raw) {
  const origin = String(raw ?? "").trim();
  if (!origin || origin === "undefined" || origin === "null") {
    return "/api";
  }
  return `${origin.replace(/\/+$/, "")}/api`;
}
