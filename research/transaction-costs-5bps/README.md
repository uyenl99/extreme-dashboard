# Five-basis-point transaction-cost rerun

Every production systematic strategy charges 0.05% on purchases and 0.05% on sales, including initial purchases. Rebalances charge only the changed dollar exposure, using drifted prior weights. A full asset switch charges both legs. Open positions are not forced closed at the final reporting date. HAA retains its clearly labeled gross/10-bps sensitivity comparisons; its main result is net 5 bps per side. Extreme OS is a live record and is unchanged.

The rerun uses existing production price, membership, capitalization, and next-open signal caches. ETF1, ETF2, HAA, Momentum Stocks, and Mean Reversion were recalculated, then the combined portfolio was rebuilt from the net equity curves. Native strategy date ranges differ; the combined result uses the shared July 3, 2017–August 31, 2026 range and rebases each strategy to $10,000 at its first shared observation. There is no additional fee or rebalancing between combined sleeves.

The engine patches in this folder document the changes applied to the adjacent local DualMom, inflationcompass, MomoSp, and RevMurphy projects. HAA already applies 5 bps per traded dollar. Keep those engine changes when moving or reinstalling the scheduled backtests. Mean Reversion now deducts entry fees immediately, deducts exit fees from actual exit proceeds, and reserves cash for entry costs. Public/member current-month marks also include the current rebalance fee.

Validation: independently replayed ETF1 and ETF2 target/drift turnover against MOO prices; checked every Momentum Stocks buy/sell fee; reconciled 1,322 Mean Reversion entry fees, 1,317 exit fees, realized P&L, and every daily cash balance; reconciled HAA net/gross curves to its fee ledger; passed execution-price checks and seven combined-portfolio tests. The shared daily batch runs `scripts/verify_transaction_costs.py` before building combined results.

| Strategy | CAGR | Sharpe | Max drawdown |
|---|---:|---:|---:|
| ETF1 | 29.0% | 1.42 | -18.9% |
| ETF2 | 21.4% | 1.22 | -24.1% |
| HAA | 12.00% | 1.14 | -15.00% |
| Momentum Stocks | 45.0% | 1.28 | -42.7% |
| Mean Reversion | 26.9% | 1.39 | -21.0% |
| Combined Portfolio | 25.75% | 1.70 | -12.04% |
