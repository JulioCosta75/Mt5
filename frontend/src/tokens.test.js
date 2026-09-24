import fs from "fs";
import path from "path";

const cssPath = path.join(__dirname, "index.css");
const css = fs.readFileSync(cssPath, "utf8");

function tokenValue(name) {
  const match = css.match(new RegExp(`${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}:\\s*([^;]+);`));
  return match ? match[1].trim() : null;
}

describe("Atlas 2 Stage 1 color tokens", () => {
  test("signal colors keep their operational hex values", () => {
    expect(tokenValue("--sig-pos")).toBe("#22C55E");
    expect(tokenValue("--sig-neg")).toBe("#EF4444");
    expect(tokenValue("--sig-warn")).toBe("#F59E0B");
    expect(tokenValue("--sig-info")).toBe("#3B82F6");
  });

  test("brand gold exists and is not a signal color", () => {
    const gold = tokenValue("--brand-gold");
    expect(gold).toBe("#C9A962");
    expect(gold).not.toBe(tokenValue("--sig-warn"));
    expect(gold).not.toBe(tokenValue("--sig-neg"));
    expect(gold).not.toBe(tokenValue("--sig-pos"));
    expect(gold).not.toBe(tokenValue("--sig-info"));
  });

  test("section heading class is uppercase with wide tracking", () => {
    expect(css).toMatch(/\.section-heading/);
    expect(css).toMatch(/\.panel-title,\s*\n\.section-heading/);
    expect(css).toMatch(/text-transform:\s*uppercase/);
    expect(css).toMatch(/letter-spacing:\s*0\.2em/);
  });

  test("alert and badge signal classes still use signal tokens, not brand gold", () => {
    expect(css).toMatch(/\.alert-row\.WARNING\s*\{\s*border-left-color:\s*var\(--sig-warn\)/);
    expect(css).toMatch(/\.alert-row\.CRITICAL\s*\{\s*border-left-color:\s*var\(--sig-neg\)/);
    expect(css).toMatch(/\.badge\.paused\s*\{[^}]*var\(--sig-warn\)/s);
    expect(css).toMatch(/\.badge\.error\s*\{[^}]*var\(--sig-neg\)/s);
    expect(css).toMatch(/\.badge\.live\s*\{[^}]*var\(--sig-pos\)/s);
    expect(css).not.toMatch(/\.alert-row\.WARNING[^}]*--brand-gold/);
    expect(css).not.toMatch(/\.badge\.paused[^}]*--brand-gold/);
  });

  test("Revolution purple identity in this stylesheet is unchanged", () => {
    expect(css).toMatch(/\.btn\.nav-revolution \{\s*color: #C4B5FD;/);
    expect(css).toMatch(/border-bottom: 2px solid #A855F7;/);
  });
});
