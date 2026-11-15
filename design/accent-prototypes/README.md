# Sr. Atlas — accent color prototypes

**Decision-only.** Not production UI. Not part of Phase 2 installer work (PR #9).
Do not implement in `Dashboard.jsx` until founders pick A or B after Phase 2 close.

## Options

| Option | Accent | Intent |
|--------|--------|--------|
| **A** | `#F5A623` amber/gold | Precision, value, premium instrument |
| **B** | `#22D3EE` cyan/teal | Technical clarity, live real-time feel |

Dark base from `design_guidelines.json` is unchanged (`#0A0A0A` / `#121212`).
Green/red remain P&L-only in the mock.

Accent is applied only to: brand wordmark, LIVE indicators, primary CTA, live numbers / live chart stroke.

## Preview (interactive, side-by-side)

Open in a browser (no build required):

```bash
# from repo root
xdg-open design/accent-prototypes/index.html
# or: python3 -m http.server 8765 --directory design/accent-prototypes
```

## Static captures

| File | What |
|------|------|
| `captures/sr-atlas-final-comparison.webp` | Browser capture of the HTML side-by-side |
| `captures/accent-option-a-amber.png` | Option A mood board / mock |
| `captures/accent-option-b-cyan.png` | Option B mood board / mock |

## Out of scope

- No changes to production `frontend/src/Dashboard.jsx` on this branch.
- No merge/deploy of accent into Phase 2 without separate founder authorization after Phase 2 close.
