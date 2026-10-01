import { resolveApiBase } from "./apiBase";
import fs from "fs";
import path from "path";

describe("resolveApiBase — never /undefined/api", () => {
  test("empty installer/same-origin values become /api", () => {
    expect(resolveApiBase(undefined)).toBe("/api");
    expect(resolveApiBase(null)).toBe("/api");
    expect(resolveApiBase("")).toBe("/api");
    expect(resolveApiBase("   ")).toBe("/api");
    expect(resolveApiBase("undefined")).toBe("/api");
    expect(resolveApiBase("null")).toBe("/api");
  });

  test("an explicit origin keeps /api as a suffix without double slashes", () => {
    expect(resolveApiBase("http://127.0.0.1:8001")).toBe("http://127.0.0.1:8001/api");
    expect(resolveApiBase("http://127.0.0.1:8001/")).toBe("http://127.0.0.1:8001/api");
  });

  test("license Free/Pro client paths stay under /api", () => {
    const base = resolveApiBase("");
    expect(`${base}/license`).toBe("/api/license");
    expect(`${base}/license/activate`).toBe("/api/license/activate");
    expect(`${base}/license`).not.toMatch(/undefined/i);
  });

  test("api.js wires axios to resolveApiBase(REACT_APP_BACKEND_URL)", () => {
    const apiSrc = fs.readFileSync(path.join(__dirname, "api.js"), "utf8");
    expect(apiSrc).toMatch(/resolveApiBase\(process\.env\.REACT_APP_BACKEND_URL\)/);
    expect(apiSrc).not.toMatch(/\$\{BACKEND_URL\}\/api/);
  });
});
