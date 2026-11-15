import fs from "fs";
import path from "path";

const supervisionSrc = fs.readFileSync(path.join(__dirname, "SupervisionPanel.jsx"), "utf8");

describe("Supervision panel MT5 terminal line", () => {
  test("shows the MT5 terminal dot after Bridge only when the field is present", () => {
    expect(supervisionSrc).toMatch(
      /<ServiceDot label="Bridge" ok=\{svc\.bridge_ok\} \/>\s*\{svc\.mt5_terminal_ok !== undefined && \(\s*<ServiceDot label="MT5 terminal" ok=\{svc\.mt5_terminal_ok\} \/>\s*\)\}\s*<ServiceDot label="Dashboard" ok=\{svc\.dashboard_ok\} \/>/
    );
  });
});
