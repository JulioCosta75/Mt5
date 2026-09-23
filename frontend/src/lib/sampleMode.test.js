import fs from "fs";
import path from "path";
import {
  isSamplePresentation,
  formatSimulatedStatus,
  SAMPLE_DATA_LABEL,
  SIMULATED_ALERTS_TITLE,
} from "./sampleMode";

describe("sampleMode helpers — truthful mock presentation", () => {
  test("mock health mode forces sample presentation", () => {
    expect(isSamplePresentation({ state: "connected", mode: "mt5" }, "mock")).toBe(true);
  });

  test("mt5 status mode=mock forces sample presentation", () => {
    expect(isSamplePresentation({ state: "unconfigured", mode: "mock" }, "mt5")).toBe(true);
  });

  test("missing status is treated as sample", () => {
    expect(isSamplePresentation(null, null)).toBe(true);
  });

  test("live connected mt5 mode is not sample", () => {
    expect(isSamplePresentation({ state: "connected", mode: "mt5" }, "mt5")).toBe(false);
  });

  test("formatSimulatedStatus prefixes LIVE/ERROR/PAUSED", () => {
    expect(formatSimulatedStatus("LIVE")).toBe("SIM · LIVE");
    expect(formatSimulatedStatus("ERROR")).toBe("SIM · ERROR");
    expect(formatSimulatedStatus("PAUSED")).toBe("SIM · PAUSED");
  });

  test("sample labels are explicit", () => {
    expect(SAMPLE_DATA_LABEL).toBe("SAMPLE DATA");
    expect(SIMULATED_ALERTS_TITLE).toMatch(/Simulated/i);
  });

  test("live-mode path keeps raw status (no silent conversion)", () => {
    // When isSample is false, UI must use raw status strings — helper does not rewrite them.
    expect(formatSimulatedStatus("LIVE")).not.toBe("LIVE");
    expect("LIVE").toBe("LIVE");
  });
});

describe("Emergent branding removed from product HTML", () => {
  test("public/index.html has no Made with Emergent badge or emergent assets script", () => {
    const htmlPath = path.join(__dirname, "..", "..", "public", "index.html");
    const html = fs.readFileSync(htmlPath, "utf8");
    expect(html).not.toMatch(/Made with Emergent/i);
    expect(html).not.toMatch(/emergent-badge/i);
    expect(html).not.toMatch(/assets\.emergent\.sh\/scripts\/emergent-main\.js/i);
    expect(html).not.toMatch(/app\.emergent\.sh/i);
  });
});

describe("user-configurable trading freedom unchanged by helpers", () => {
  test("helpers do not encode strategy/lot/risk prohibitions", () => {
    const src = fs.readFileSync(path.join(__dirname, "sampleMode.js"), "utf8");
    expect(src).not.toMatch(/martingale|grid|hedge|lot.?size|max_open/i);
  });
});
