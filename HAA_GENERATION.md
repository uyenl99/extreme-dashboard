# HAA weekday updates

HAA is the sixth stage of the existing **Extreme Dashboard - Sequential Strategy Updates** Windows task. The task starts Monday–Friday at **3:00 PM Pacific** on this PC. Its bootstrap fetches production `main` before invoking the batch, so merged updates are used on the next run. No additional scheduled task is required.

`scripts/update_haa_weekdays.ps1` loads an isolated Python dependency directory at `C:\junk\stocks\HAA\.packages` (installing `requirements-haa.txt` if needed), then runs `scripts/refresh_haa.py`. Temporary calculations are stored beneath `C:\junk\stocks\HAA\runtime` and cleaned up. The shared batch supplies the current site checkout and handles all publication.

Each run:

1. Use the NYSE calendar, including holidays and early closes, to determine the latest finished session and last fully completed month.
2. Download fresh dividend-adjusted ETF histories and recalculate both the PDBC main test and DBC proxy extension through the last completed month. The required month-end must exist in the results.
3. Refresh the confirmed allocation's raw-price/total-return snapshot through the latest finished session. Reject stale or missing prices; never publish a fresh date over stale data.
4. Rebuild public/member pages and both strategy cards. Run return, allocation and public/member boundary checks.
5. Include `haa.html`, `api/_member-content/haa.html` and `data/haa` in the shared preview, then publish only after the existing batch guards and Vercel checks pass.

An intramonth run updates the partial-month position panel. On the last trading day, after the close, the newly finished month enters the backtest and the new allocation is labeled for the following month. A weekday market holiday retains the last completed session's date. HAA keeps its documented month-end-close execution; it is not changed to the other strategies' MOO convention. Email delivery is not enabled.

## Manual checks and rebuilds

With `requirements-haa.txt` installed and the site root on `PYTHONPATH`:

```
python scripts/refresh_haa.py
python scripts/test_haa_refresh.py
python scripts/verify_haa_page.py
node scripts/verify_haa_integration.js
```

`refresh_haa.py --as-of <timezone-aware timestamp>` is available for reproducible checks. It does not publish by itself. `generate_haa_page.py` renders the checked-in snapshot without fetching; `--refresh-snapshot` refreshes only its current prices and is not a substitute for the full calendar-aware batch.

`research/haa_backtest.py --end 2026-09-01` reproduces the original historical cutoff. `--end` is exclusive and must be the first of a month. `--refresh` bypasses raw-data caches, `--output-root` selects isolated output, and `--skip-chart` omits the optional matplotlib image. The public charts use the site's shared Plotly helper. The generator's date labels follow the input data automatically.
