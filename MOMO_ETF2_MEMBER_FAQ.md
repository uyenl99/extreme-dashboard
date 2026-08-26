# Momentum ETF2 Member FAQ

This FAQ explains the member-facing Momentum ETF2 service without disclosing
the proprietary or implementation-level strategy rules, parameters, thresholds,
data transformations, or source code.

## What is Momentum ETF2?

Momentum ETF2 is a monthly ETF rotation model based on market regime conditions.
The member page labels the model as Inflation Compass because it evaluates both
market growth conditions and inflation expectations.

The model assigns the next monthly allocation to one of a small set of ETF
holdings based on the current regime.

## What does the strategy try to do?

The strategy tries to match ETF exposure to the broader macro environment. It
can favor growth-sensitive, inflation-sensitive, defensive equity, or blended
defensive allocations depending on the model state.

It is not designed to trade intraday moves. It is a monthly regime model.

## What allocations can members see?

The public member dashboard may show one of these model allocations:

- `XLE`
- `XLK`
- `XLU`
- `XLP / IEF`

The `XLP / IEF` allocation means buying `XLP` with 50% of the model portfolio
and `IEF` with the other 50%.

## What are the four regimes?

The member page summarizes the model using four broad regimes:

- Growth up and inflation on: reflation
- Growth up and inflation off: goldilocks
- Growth down and inflation on: stagflation
- Growth down and inflation off: slowdown

These regime names are descriptive labels for the current model state. They are
not market predictions.

## How often is Momentum ETF2 updated?

Momentum ETF2 is refreshed automatically on weekdays as part of the Momentum
strategy update batch.

The documented scheduled task runs Monday through Friday at 4:00 PM Pacific
time. If no new completed market or macro data is available, the dashboard may
not materially change.

## What data does the update use?

The automated update refreshes public market and macro data sources, then
regenerates the Momentum ETF2 dashboard assets.

Members do not need to download or process data. The website displays the
latest published model output after the automated refresh completes.

## What does the current allocation mean?

The current allocation is the model's holding for the effective month shown on
the dashboard.

The signal is based on completed month-end information. That means the model
does not use incomplete future data to decide the current month's allocation.

## What does the next holding mean?

The next holding shows the model allocation determined by the latest completed
signal period. If the allocation changed, members may see that reflected in the
latest alert or trade history.

The alert is a model update, not personalized financial advice.

## How are monthly entries and exits placed?

The model assumes market-on-open (MOO) exit and entry orders on the first
trading day of each month.

## Why can the allocation stay the same for several months?

Momentum ETF2 only changes when the underlying regime changes enough to select
a different allocation. If the regime remains stable, the model can continue
holding the same ETF or blend across multiple months.

Low turnover is normal for this type of monthly regime strategy.

## What does the monthly returns table show?

The monthly returns table shows completed model returns by calendar month and
year. For an incomplete year, the year-to-date number may change as additional
months are completed.

Monthly returns compound, so yearly return is not calculated by simply adding
the monthly percentages.

## What does the equity curve show?

The equity curve shows the simulated growth of the Momentum ETF2 model compared
with SPY. It is useful for seeing long-term behavior, drawdowns, and periods of
outperformance or underperformance.

It should not be interpreted as verified live account performance.

## What does drawdown mean?

Drawdown measures how far the model has fallen from a prior high. The dashboard
may show both monthly and daily drawdown information.

Daily drawdown can be larger than monthly drawdown because it captures
intra-month movement.

## Can Momentum ETF2 lose money?

Yes. The strategy can lose money. It can also underperform SPY for days,
months, years, or longer periods.

The model is concentrated and can experience meaningful drawdowns when its
selected allocation is out of favor.

## Does Momentum ETF2 always beat SPY?

No. SPY is shown as a benchmark for comparison, not as a promise that the model
will outperform.

Momentum ETF2 can lag SPY, especially when the market environment favors assets
outside the model's current allocation.

## Why can my account differ from the dashboard?

Actual member results can differ because of:

- Entry and exit timing
- Bid/ask spreads
- Broker fills
- Taxes
- Commissions or fees
- Fractional share availability
- Account size
- Cash drag
- Missed or delayed rebalances
- Differences between model prices and personal execution prices

The dashboard shows model output, not individualized account performance.

## Is this financial advice?

No. Momentum ETF2 is an educational and research-oriented model. Members are
responsible for their own trading decisions, position sizing, taxes, and risk
tolerance.

Members should consult a qualified financial professional before making
investment decisions.

## What happens if the update is delayed?

If the local computer, data providers, internet connection, GitHub, or hosting
pipeline has an issue, the Momentum ETF2 dashboard may update late.

When this happens, the most recently published dashboard remains visible until
the next successful refresh.

## What is the main thing to remember?

Momentum ETF2 is a monthly market-regime ETF rotation model. It publishes the
current allocation, regime state, backtest summary, return table, drawdown
information, and recent allocation changes, but it does not guarantee returns
or provide individualized financial advice.
