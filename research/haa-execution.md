# HAA scheduled model

The shared weekday batch runs `scripts/update_haa_weekdays.ps1`, which refreshes `research/haa_backtest.py` and renders the public and protected HAA pages. SGOV replaces BIL in both the defensive IEF comparison and holdings. Signals use 1/3/6/12-month total-return momentum at month-end; fills use the next trading session open. Costs remain 5bp per dollar bought or sold.

Adjusted opens use raw open multiplied by adjusted close / raw close. Old holdings earn the overnight gap before the rebalance; new targets earn open-to-close returns. These historical opens are auction-fill proxies. Benchmarks use opening execution too. The separate MOC comparison retains same-close fills. Metrics end at the last complete month; no next-month fill or forced liquidation is included at the endpoint.

SGOV history starts June 2020. After the momentum warmup, the first signal is June 30, 2021 and first fill July 1, 2021. DBC is now a commodity sensitivity over the same dates, not a longer history. Historical SGOV returns are not backfilled.

Closing portfolio weights are persisted with completed-month results. The partial-month snapshot replays the next opening rebalance from these drifted weights and includes the overnight return and both-sided trading costs. At month-end, the latest target is marked pending and previous holdings remain in effect until the next session opens. Position entries use raw opening prices; position returns begin at that fill. Overall month-to-date return also includes the preceding overnight gap and rebalance cost.

Validation: `scripts/test_haa_refresh.py`, `scripts/verify_haa_page.py`, and `scripts/verify_haa_integration.js`. The refresh executes both Python checks before shared publication proceeds. The initial SGOV/MOO refresh through August 2026 reproduces the separate comparison: 10.49% CAGR, -13.23% daily-close maximum drawdown, 62 holding months. Small vendor adjustment revisions can change unrounded values.
