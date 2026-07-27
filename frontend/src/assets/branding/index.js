// Central export for all Forge Factory Lab / Sr. Atlas branding assets.
// Official assets live in the sub-folders below. To update a logo, replace the
// file keeping the same name (or change the extension here) — no other code
// changes are required across the app.
//
//   sr-atlas/logo-round.png    -> favicon, app icon, header badge, boot, avatar
//   forge-factory/logo.png     -> welcome, loading, about, documentation
//
// Brand hierarchy:
//   Forge Factory Lab = the company / laboratory / engineering environment.
//   Sr. Atlas         = the AI supervisor / orchestration system / dashboard.

import srAtlasRound from "./sr-atlas/logo-round.png";
import forgeFactoryLogo from "./forge-factory/logo.png";

// Sr. Atlas round emblem doubles as the compact icon (favicon / nav / badge).
const srAtlasIcon = srAtlasRound;
// Header lockup uses the round emblem + wordmark composed in the UI.
const srAtlasHorizontal = srAtlasRound;

export const brand = {
  srAtlas: {
    name: "Sr. Atlas",
    role: "AI Supervisor",
    round: srAtlasRound,
    icon: srAtlasIcon,
    horizontal: srAtlasHorizontal,
  },
  forgeFactory: {
    name: "Forge Factory Lab",
    role: "Engineering Laboratory",
    logo: forgeFactoryLogo,
  },
};

export { srAtlasRound, srAtlasIcon, srAtlasHorizontal, forgeFactoryLogo };
export default brand;
