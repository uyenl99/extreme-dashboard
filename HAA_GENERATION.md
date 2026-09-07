# Hybrid Asset Allocation page

Public page: `haa.html`. Protected page: `api/_member-content/haa.html`, served through the existing authenticated `/api/member-page?strategy=haa` route. Cards appear after ETF2 in both directories; the homepage ETF group links to HAA.

## Rebuild the current published snapshot

Install the existing site requirements (pandas, numpy, requests, plotly). From the site root:

```
python generate_haa_page.py
```

Input CSVs and `current_snapshot.json` are checked in under `data/haa`, which is excluded from Vercel publication by the existing `.vercelignore`. The generator updates both pages and both card metric blocks. It uses the shared chart/card helpers and the same daily, zero-risk-free-rate Sharpe convention as ETF1. All returns are net of the declared trading costs. Main equity is scaled to $100,000 to match ETF1/2. Main metrics use complete months only.

To update the separate current holding snapshot from public Yahoo Finance daily bars:

```
python generate_haa_page.py --refresh-snapshot
```

The snapshot marks the latest confirmed month-end weights, not a new signal. It is rejected if its signal date differs from the CSV target date or if it extends beyond the next holding month. Prices are raw closes; position total P/L includes adjusted total returns/distributions. It has no trade execution or email capability.

## Reproduce the historical calculations

`research/haa_backtest.py` preserves the backtest implementation with an explicit September 1, 2026 exclusive cutoff. It requires matplotlib in addition to site requirements. Run it to create `research/haa_run/results` and cache vendor responses in `research/haa_run/data`. Copy its result CSVs into `data/haa` and run the page generator. Change the cutoff deliberately for a new complete-month sample and update dated report labels as necessary; do not mark a partial month as complete.

The PDBC actual-ETF test and DBC proxy extension are separate. Preserve their distinct dates and labels. Same-close execution is idealized; next-close sensitivity is included. The article's 1971 history and 15.9% CAGR are not used as our site's performance.

HAA has not been added to the automatic daily scheduler or member emails. Existing daily jobs preserve unrelated cards and pages. Displayed snapshot dates remain authoritative.

## Verification

```
python scripts/verify_haa_page.py
node scripts/verify_haa_integration.js
```

These validate published metrics, all 129 monthly observations, historical weight alignment, absence of member holdings in public HTML, membership enforcement, and unequal-weight position sizing while retaining the existing ETF equal-weight path.
