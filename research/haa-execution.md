# HAA scheduled model

The shared weekday batch runs `scripts/update_haa_weekdays.ps1`, which refreshes `research/haa_backtest.py` and renders the public and protected HAA pages. The cash ETF is BIL before SGOV is available, then SGOV, in both the defensive IEF comparison and holdings. Signals use 1/3/6/12-month total-return momentum at month-end; fills use the next trading session open. Costs remain 5bp per dollar bought or sold.

Adjusted opens use raw open multiplied by adjusted close / raw close. Old holdings earn the overnight gap before the rebalance; new targets earn open-to-close returns. These historical opens are auction-fill proxies. Benchmarks use opening execution too. The separate MOC comparison retains same-close fills. Metrics end at the last complete month; no next-month fill or forced liquidation is included at the endpoint.

SGOV history starts June 1, 2020. BIL provides the earlier cash history. Momentum uses BIL total returns through the first SGOV close, then SGOV total returns, linked at that common close without a price-level discontinuity. At the June 30, 2020 signal, SGOV becomes eligible for the next-session fill on July 1. Trading uses separately tracked actual BIL and SGOV holdings and charges turnover on any switch. SGOV is never held before inception; missing SGOV observations after inception fail the refresh instead of silently reverting to BIL.

This restores the main test to December 2015 onward and the DBC commodity-proxy extension to June 2008 onward. The first 12 months of common history remain reserved for momentum.

Closing portfolio weights are persisted with completed-month results. The partial-month snapshot replays the next opening rebalance from these drifted weights and includes the overnight return and both-sided trading costs. At month-end, the latest target is marked pending and previous holdings remain in effect until the next session opens. Position entries use raw opening prices; position returns begin at that fill. Overall month-to-date return also includes the preceding overnight gap and rebalance cost.

Validation: `scripts/test_haa_refresh.py`, `scripts/verify_haa_page.py`, and `scripts/verify_haa_integration.js`. The refresh executes both Python checks before shared publication proceeds. The fallback rerun uses the longer history; generated summary.csv is the source for current metrics. Small vendor adjustment revisions can change unrounded values.
