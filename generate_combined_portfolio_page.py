"""Combine production equity curves, rebasing each sleeve to $10,000.

Run from any directory with Python and the site's pandas/plotly dependencies.
Only common observed sessions are accepted; missing sessions fail rather than
silently carrying forward stale equity. No inter-strategy rebalancing is assumed.
"""
import argparse
import calendar
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from combined_portfolio_template import render_page, replace_card

ROOT = Path(__file__).resolve().parent
START_PER_STRATEGY = 10_000.0


def read_curve(path, date_column, columns):
    frame = pd.read_csv(path)
    dates = pd.to_datetime(frame.iloc[:, 0] if date_column is None else frame[date_column])
    result = frame[list(columns)].astype(float).rename(columns=columns)
    result.index = pd.DatetimeIndex(dates, name="Date")
    if (len(result) < 2 or result.index.hasnans or result.index.has_duplicates
            or not result.index.is_monotonic_increasing
            or not np.isfinite(result.to_numpy()).all() or (result <= 0).any().any()):
        raise ValueError(f"Invalid dates or equity values in {path}")
    return result


def combine_curves(etf1, haa, mean_reversion):
    curves = (etf1, haa, mean_reversion)
    start = max(frame.index.min() for frame in curves)
    end = min(frame.index.max() for frame in curves)
    trimmed = [frame.loc[start:end] for frame in curves]
    if len(trimmed[0]) < 2:
        raise ValueError("Strategy curves need at least two overlapping sessions")
    if any(not trimmed[0].index.equals(frame.index) for frame in trimmed[1:]):
        raise ValueError("Strategy curves have missing or mismatched sessions in the shared period")
    combined = pd.concat(trimmed, axis=1)
    combined = combined.div(combined.iloc[0]).mul(START_PER_STRATEGY)
    combined["Equity"] = combined[["ETF1", "HAA", "Mean Reversion"]].sum(axis=1)
    combined["SPY_Equity"] *= 3
    combined["60/40_Equity"] *= 3
    return combined.reset_index()


COMPARISONS = (("Equity", "Combined Portfolio", "#60a5fa"),
               ("SPY_Equity", "SPY", "#94a3b8"),
               ("60/40_Equity", "60/40 (SPY/IEF)", "#a78bfa"))


def build_comparison_chart(daily):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.67, 0.33], vertical_spacing=0.09,
                        subplot_titles=("Equity", "Drawdown"))
    for column, label, color in COMPARISONS:
        for row, values in ((1, daily[column]), (2, daily[column] / daily[column].cummax() - 1)):
            fig.add_trace(go.Scatter(
                x=daily.Date, y=values, name=label, legendgroup=column,
                showlegend=row == 1, mode="lines", line=dict(color=color, width=2),
                hovertemplate=("%{y:$,.0f}<extra>%{fullData.name}</extra>" if row == 1
                               else "%{y:.2%}<extra>%{fullData.name}</extra>")), row=row, col=1)
    fig.update_layout(template="plotly_dark", height=720, hovermode="x unified",
                      paper_bgcolor="#111827", plot_bgcolor="#111827",
                      margin=dict(l=65, r=25, t=85, b=45),
                      legend=dict(orientation="h", y=1.14, x=0))
    fig.update_yaxes(title_text="Equity ($)", tickprefix="$", tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown", tickformat=".0%", rangemode="tozero", row=2, col=1)
    fig.update_xaxes(gridcolor="#273449")
    fig.update_yaxes(gridcolor="#273449")
    return fig


def period_returns(daily):
    equity = daily.set_index("Date")[[item[0] for item in COMPARISONS]]
    ends = equity.groupby(equity.index.to_period("M")).last()
    returns = ends.pct_change()
    returns.iloc[0] = ends.iloc[0] / equity.iloc[0] - 1
    return returns


def build_comparison_monthly_table(daily):
    returns = period_returns(daily)
    headers = ["Year", *calendar.month_abbr[1:], "Year Return", "SPY Return", "60/40 Return"]
    rows = []
    for year in sorted(set(returns.index.year), reverse=True):
        subset = returns[returns.index.year == year]
        values = [subset.loc[pd.Period(year=year, month=month, freq="M"), "Equity"]
                  if pd.Period(year=year, month=month, freq="M") in subset.index else np.nan
                  for month in range(1, 13)]
        values.extend(((1 + subset).prod() - 1).tolist())
        cells = []
        for value in values:
            if pd.isna(value):
                cells.append('<td class="muted">—</td>')
            else:
                css = "positive" if value > 0 else "negative" if value < 0 else "muted"
                cells.append(f'<td class="{css}">{value:.1%}</td>')
        rows.append(f'<tr><th scope="row">{year}</th>{"".join(cells)}</tr>')
    return ('<p class="subtle">Jan–Dec show Combined Portfolio monthly returns. '
            'The last three columns show compounded returns for each year over the same available dates; '
            'the first and last years may be partial. 60/40 is 60% SPY / 40% IEF, rebalanced monthly, '
            'with 5-basis-point trading costs. Latest returns through '
            f'{daily.Date.iloc[-1]:%Y-%m-%d}.</p>'
            '<style>.combined-monthly-table th,.combined-monthly-table td{font-size:15px;line-height:1.5;padding:10px 12px}</style>'
            '<div class="table-wrap combined-monthly-table"><table><thead><tr>'
            + ''.join(f'<th scope="col">{label}</th>' for label in headers)
            + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def summarize(daily):
    equity = daily.set_index("Date")["Equity"]
    spy = daily.set_index("Date")["SPY_Equity"]
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    returns = equity.pct_change().dropna()
    volatility = returns.std(ddof=1)
    spy_returns = spy.pct_change().dropna()
    spy_volatility = spy_returns.std(ddof=1)
    summary = pd.Series({
        "cagr": (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1,
        "daily_max_drawdown": (equity / equity.cummax() - 1).min(),
        "total_return": equity.iloc[-1] / equity.iloc[0] - 1,
        "sharpe": returns.mean() / volatility * np.sqrt(252) if volatility > 0 else 0.0,
        "spy_cagr": (spy.iloc[-1] / spy.iloc[0]) ** (1 / years) - 1,
        "spy_sharpe": spy_returns.mean() / spy_volatility * np.sqrt(252) if spy_volatility > 0 else 0.0,
        "spy_daily_max_drawdown": (spy / spy.cummax() - 1).min(),
        "final": equity.iloc[-1],
    })
    month_ends = equity.groupby(equity.index.to_period("M")).last()
    monthly_returns = month_ends.pct_change()
    monthly_returns.iloc[0] = month_ends.iloc[0] / equity.iloc[0] - 1
    rows = []
    for year in sorted(set(monthly_returns.index.year)):
        subset = monthly_returns[monthly_returns.index.year == year]
        row = {"Year": year, **{name: np.nan for name in calendar.month_abbr[1:]}}
        for period, value in subset.items():
            row[calendar.month_abbr[period.month]] = value
        row["Year Return"] = (1 + subset).prod() - 1
        rows.append(row)
    partial = None
    if equity.index[-1] < equity.index[-1] + pd.offsets.BMonthEnd(0):
        partial = {"latest_day": equity.index[-1].strftime("%Y-%m-%d"),
                   "partial_return": monthly_returns.iloc[-1]}
    return summary, pd.DataFrame(rows), monthly_returns, partial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--etf1-source", type=Path, default=ROOT.parent / "DualMom/output_momo5")
    parser.add_argument("--haa-source", type=Path, default=ROOT / "data/haa")
    parser.add_argument("--mean-reversion-source", type=Path,
                        default=ROOT.parent / "RevMurphy/output_long_only_5x0_100_no_cluster_next_open")
    parser.add_argument("--output", type=Path, default=ROOT / "combined-portfolio.html")
    parser.add_argument("--strategies-page", type=Path, default=ROOT / "strategies.html")
    args = parser.parse_args()
    etf1 = read_curve(args.etf1_source / "daily_equity_entries_exits.csv", "Date",
                      {"Equity": "ETF1", "SPY_Equity": "SPY_Equity"})
    haa = read_curve(args.haa_source / "exact_etfs_daily_equity.csv", None,
                     {"HAA net 5bp": "HAA", "60 SPY 40 IEF": "60/40_Equity"})
    mr = read_curve(args.mean_reversion_source / "equity_curve.csv", "date", {"equity": "Mean Reversion"})
    daily = combine_curves(etf1, haa, mr)
    summary, monthly, months, partial = summarize(daily)
    description = (
        "ETF1, Hybrid Asset Allocation (HAA), and Mean Reversion each start with $10,000, "
        "for $30,000 total. Each strategy compounds independently; there is no rebalancing between strategies. "
        "The curves are rebased at the first shared observation and stop at the latest shared session. "
        "Each strategy includes 5 bps (0.05%) on buys and 5 bps on sells. The combined curve adds no further trading fee. HAA uses the exact-ETF series; Mean Reversion uses the "
        "production long-only 5-position, next-day market-on-open model. "
        "SPY and 60/40 start with the same $30,000. Sharpe uses daily returns, 252 sessions per year, and a zero "
        "risk-free rate. First and last calendar periods may be partial. "
    )
    page = render_page(summary, daily, months, monthly, {}, partial,
                       results_only=True, title="Combined Portfolio", description=description,
                       chart_html=build_comparison_chart(daily).to_html(
                           full_html=False, include_plotlyjs="cdn", config={"responsive": True},
                           div_id="combined-equity-drawdown-chart"),
                       monthly_html=build_comparison_monthly_table(daily),
                       chart_description="Equity and drawdown compared with SPY and 60/40 (60% SPY / 40% IEF), each starting at $30,000. Drawdown measures the decline from each portfolio's previous peak.")
    args.output.write_text(page, encoding="utf-8")
    cards = args.strategies_page.read_text(encoding="utf-8")
    cards = replace_card(cards, "Combined Portfolio", summary.cagr, summary.sharpe,
                         summary.daily_max_drawdown, summary.spy_daily_max_drawdown,
                         summary.spy_cagr, summary.spy_sharpe)
    args.strategies_page.write_text(cards, encoding="utf-8")
    member_page = args.strategies_page.with_name("members.html")
    if member_page.is_file():
        member_cards = replace_card(member_page.read_text(encoding="utf-8"), "Combined Portfolio",
                                    summary.cagr, summary.sharpe, summary.daily_max_drawdown,
                                    summary.spy_daily_max_drawdown, summary.spy_cagr, summary.spy_sharpe)
        member_page.write_text(member_cards, encoding="utf-8")

    print(f"Generated {args.output}: {daily.Date.iloc[0]:%Y-%m-%d} through {daily.Date.iloc[-1]:%Y-%m-%d}; "
          f"starting $30,000; final ${summary['final']:,.2f}")


if __name__ == "__main__":
    main()
