# Branding Assets — Forge Factory Lab / Sr. Atlas

This folder holds all official branding assets used across the application.

```
branding/
├── sr-atlas/
│   ├── logo-horizontal.svg   # main lockup — dashboard header, boot screen
│   ├── logo-round.svg        # round badge version
│   └── icon.svg              # SA icon — favicon, app icon, nav icon
└── forge-factory/
    └── logo.svg              # company logo — welcome, loading, about, docs
```

## Brand hierarchy

- **Forge Factory Lab** — the company / laboratory / engineering environment.
- **Sr. Atlas** — the AI Supervisor / orchestration system / dashboard identity.

## Swapping in the OFFICIAL assets

The files currently committed here are **temporary placeholders**. To install the
official assets, simply **overwrite each file keeping the same filename**. No code
changes are required — every component reads through `assets/branding/index.js`.

- Prefer `.svg` for crisp scaling. If you use raster files (`.png` / `.webp`),
  keep the same base name and update the matching import extension in
  `index.js` (and, for the browser tab icon, `public/favicon.svg`
  + the `<link rel="icon">` tags in `public/index.html`).
- Do **not** redesign or recreate the logos — use the supplied files as provided.
