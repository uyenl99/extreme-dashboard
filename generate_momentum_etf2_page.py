import argparse
import html
import json
from pathlib import Path

import pandas as pd

from strategy_faq import FAQ_CSS, render_faq
from metric_style import metric_class
from strategy_benchmark import yearly_returns_by_year
from strategy_card import update_backtest_card, update_member_backtest_card
from strategy_chart import build_equity_drawdown_chart


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Momentum ETF2 public or member page.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audience", choices=("public", "member"), default="public")
    parser.add_argument("--chart-src", default="inflation-compass/wealth.png")
    parser.add_argument(
        "--strategies-page",
        type=Path,
        default=Path("strategies.html"),
        help="Strategies page whose MoMoEtf2 card metrics should be refreshed.",
    )
    parser.add_argument(
        "--members-page",
        type=Path,
        default=Path("members.html"),
        help="Authenticated strategy directory whose MoMoEtf2 metrics should be refreshed.",
    )
    return parser.parse_args()


def pct(value, decimals=2):
    return f"{float(value) * 100:.{decimals}f}%"


def currency(value):
    return f"${float(value):,.0f}"


def table(frame, percent_columns=()):
    headers = "".join(f"<th>{html.escape(str(column))}</th>" for column in frame.columns)
    rows = []
    for row in frame.itertuples(index=False, name=None):
        cells = []
        for column, value in zip(frame.columns, row):
            if pd.isna(value) or value == "":
                text, css = "—", "muted"
            elif column in percent_columns:
                number = float(value)
                text = f"{number * 100:.2f}%"
                css = "positive" if number > 0 else "negative" if number < 0 else "muted"
            else:
                text, css = html.escape(str(value)), ""
            cells.append(f'<td class="{css}">{text}</td>')
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def build_chart(daily, start_equity=100000.0):
    return build_equity_drawdown_chart(
        daily.index,
        daily["strategy_wealth"] * start_equity,
        daily["spy_wealth"] * start_equity,
        "MoMoEtf2",
        "momoetf2-equity-chart",
    )


def build_monthly_table(monthly, daily):
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    headers = "".join(f"<th>{name}</th>" for name in month_names + ["Year Return", "SPY Year"])
    spy_year = yearly_returns_by_year(daily.index, daily["spy_wealth"])
    rows = []
    for item in monthly.sort_values("Year", ascending=False).itertuples(index=False):
        values = [getattr(item, name) for name in month_names]
        values.extend((getattr(item, "_13"), spy_year.get(int(item.Year))))
        cells = []
        for value in values:
            if pd.isna(value) or value == "":
                cells.append('<td class="muted">—</td>')
            else:
                number = float(value)
                css = "positive" if number > 0 else "negative" if number < 0 else "muted"
                cells.append(f'<td class="{css}">{number * 100:.1f}%</td>')
        rows.append(f"<tr><th>{int(item.Year)}</th>{''.join(cells)}</tr>")
    return (
        '<div class="table-wrap"><table><thead><tr><th>Year</th>'
        f'{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def allocation_history(monthly_backtest, limit=20):
    data = monthly_backtest.copy()
    data.index = pd.PeriodIndex(data.index.astype(str), freq="M")
    display = pd.DataFrame(index=data.index)
    display["Month"] = data.index.astype(str)
    display["Holdings"] = data["held"]
    display["Return"] = data["strategy_return"]
    display["SPY"] = data["spy_return"]
    return display.sort_index(ascending=False).head(limit).reset_index(drop=True)


def extend_daily_to_partial(daily, close_prices, open_prices, alert):
    """Append the current holding's open-to-latest-close mark without closing the month."""
    original_index_name = daily.index.name
    latest_day = pd.Timestamp(close_prices.index.max())
    current_period = latest_day.to_period("M")
    period_days = close_prices.index[
        pd.PeriodIndex(close_prices.index, freq="M") == current_period
    ]
    if period_days.empty:
        return daily, None, None
    entry_date = pd.Timestamp(period_days[0])
    if entry_date < pd.Timestamp(daily.index.max()):
        return daily, None, None

    holding = str(alert["current_holding"])
    weights = {"XLP": 0.5, "IEF": 0.5} if holding == "XLP/IEF" else {holding: 1.0}
    missing = [
        ticker for ticker in (*weights, "SPY")
        if ticker not in close_prices or ticker not in open_prices
    ]
    if missing:
        raise ValueError("Missing current-month prices for: " + ", ".join(missing))

    base_strategy = float(daily.iloc[-1]["strategy_wealth"])
    base_spy = float(daily.iloc[-1]["spy_wealth"])
    additions = []
    for day in period_days:
        strategy_growth = sum(
            weight * close_prices.at[day, ticker] / open_prices.at[entry_date, ticker]
            for ticker, weight in weights.items()
        )
        spy_growth = close_prices.at[day, "SPY"] / open_prices.at[entry_date, "SPY"]
        additions.append({
            "date": day,
            "holding": holding,
            "strategy_wealth": base_strategy * strategy_growth,
            "spy_wealth": base_spy * spy_growth,
            "switched": False,
        })
    extended = (
        pd.concat([daily.reset_index(names="date"), pd.DataFrame(additions)], ignore_index=True)
        .drop_duplicates("date", keep="last")
        .set_index("date")
        .sort_index()
    )
    extended.index.name = original_index_name
    extended["strategy_return"] = extended["strategy_wealth"].pct_change()
    extended["spy_return"] = extended["spy_wealth"].pct_change()
    for name in ("strategy", "spy"):
        extended[f"{name}_drawdown"] = (
            extended[f"{name}_wealth"] / extended[f"{name}_wealth"].cummax() - 1
        )
    return extended, strategy_growth - 1, spy_growth - 1


def current_month_panel(daily, alert, partial_return):
    latest_day = pd.to_datetime(daily.index).max()
    current_period = latest_day.to_period("M")
    month_return = float(partial_return) if partial_return is not None else 0.0
    holding = str(alert["current_holding"])
    return_class = "positive" if month_return > 0 else "negative" if month_return < 0 else "muted"
    return (
        '<section class="panel" id="current-month"><h2>Current Partial Month</h2>'
        f'<p class="subtle">Mark-to-market through {latest_day:%Y-%m-%d}; this is an incomplete-month estimate.</p>'
        '<div class="metrics">'
        f'<div class="metric"><div class="metric-label">Current Month Return</div><div class="metric-value {return_class}">{pct(month_return)}</div></div>'
        f'<div class="metric"><div class="metric-label">Holding</div><div class="metric-value positive">{html.escape(holding)}</div></div>'
        f'<div class="metric"><div class="metric-label">Effective Month</div><div class="metric-value">{current_period}</div></div>'
        '</div></section>'
    )


def latest_alert_table(daily, alert):
    latest_day = pd.to_datetime(daily.index).max()
    frame = pd.DataFrame([{
        "Signal": str(alert["signal_month_end"]),
        "Holding": alert["next_holding"],
        "Execution": f'{alert["effective_month"]} open',
        "Changed": "Yes" if bool(alert["allocation_changed"]) else "No",
        "Status": f"Preliminary through {latest_day:%Y-%m-%d}",
    }])
    return table(frame)


def render(source, audience, chart_src):
    summary = pd.read_csv(source / "summary.csv", index_col=0)
    monthly = pd.read_csv(source / "monthly_pnl_by_year.csv")
    monthly_backtest = pd.read_csv(source / "monthly_backtest.csv", index_col=0)
    daily = pd.read_csv(source / "daily_drawdown.csv", index_col=0, parse_dates=True)
    close_prices = pd.read_csv(source / "adjusted_close_prices.csv", index_col=0, parse_dates=True)
    open_prices = pd.read_csv(source / "adjusted_open_prices.csv", index_col=0, parse_dates=True)
    alert = json.loads((source / "latest_alert.json").read_text(encoding="utf-8"))
    daily, partial_return, _ = extend_daily_to_partial(
        daily, close_prices, open_prices, alert
    )
    strategy = summary.iloc[:, 0]
    spy = summary.iloc[:, 1]
    start_equity = 100000.0
    start_date = pd.to_datetime(daily.index).min().strftime("%Y-%m-%d")
    end_date = pd.to_datetime(daily.index).max().strftime("%Y-%m-%d")
    active_months = int(monthly[["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]].count(axis=1).sum())
    final_equity = float(strategy["Growth of $1"]) * start_equity
    metrics = (
        ("Strategy CAGR", pct(strategy["CAGR"], 1)),
        ("SPY CAGR", pct(spy["CAGR"], 1)),
        ("Strategy Max Drawdown", pct(strategy["Daily max drawdown"], 1)),
        ("SPY Max Drawdown", pct(spy["Daily max drawdown"], 1)),
        ("Total Return", pct(float(strategy["Growth of $1"]) - 1)),
        ("Sharpe Ratio", f'{float(strategy["Sharpe"]):.2f}'),
        ("Final Equity", currency(final_equity)),
        ("Active Months", f"{active_months:,}"),
    )
    metrics_html = "".join(
        f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value {metric_class(value)}">{value}</div></div>'
        for label, value in metrics
    )
    if audience == "member":
        allocations = allocation_history(monthly_backtest)
        protected = (
            current_month_panel(daily, alert, partial_return)
            + '<section class="panel enlarged-table"><h2>Latest Alert</h2>'
            + '<p class="subtle">The current-month signal is preliminary until month end and may change before execution.</p>'
            + latest_alert_table(daily, alert)
            + '</section>'
            + '<section class="panel enlarged-table"><h2>Latest 20 Historical Trades</h2>'
            + table(allocations, ("Return", "SPY"))
            + '</section>'
        )
        before_results = protected
        after_results = ""
    else:
        protected = (
            '<section class="panel"><h2>Member Signals</h2><p class="subtle">Current allocation details, latest alerts, and recent model updates are available to members.</p>'
            '<p><a href="subscribe.html">View membership options</a></p></section>'
        )
        before_results = ""
        after_results = protected
    chart_html = build_chart(daily, start_equity)
    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MoMoEtf2 Backtest - Extreme Trading Inc.</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial,Helvetica,sans-serif}}nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 30px;background:#111827}}nav a{{color:white;text-decoration:none;margin-left:20px}}a{{color:#60a5fa}}.container{{width:95%;max-width:1400px;margin:auto;padding:30px 20px 60px}}.hero,.panel{{background:#111827;border:1px solid #374151;border-radius:12px;padding:26px;margin-bottom:22px}}.eyebrow{{color:#60a5fa;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:bold}}h1{{margin:8px 0 10px}}h2{{margin-top:0}}.subtle,.muted{{color:#94a3b8}}.metrics{{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:14px;margin:22px 0}}.metric{{background:#111827;border:1px solid #374151;border-radius:10px;padding:18px}}.metric-label{{color:#94a3b8;font-size:13px}}.metric-value{{font-size:24px;font-weight:700;margin-top:6px}}.chart{{overflow:hidden}}.positive{{color:#22c55e}}.negative{{color:#f87171}}.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;background:#111827}}th,td{{border:1px solid #374151;padding:7px 9px;text-align:right;font-size:12px;white-space:nowrap}}.enlarged-table th,.enlarged-table td{{font-size:15px}}th{{background:#1f2937;color:white}}th:first-child,td:first-child{{text-align:left}}.disclaimer{{font-size:13px;line-height:1.6;color:#94a3b8}}footer{{text-align:center;padding:30px;color:#94a3b8}}@media(max-width:800px){{nav{{align-items:flex-start;padding:16px;gap:12px}}nav div:last-child{{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}}nav a{{margin-left:8px;font-size:12px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.container{{padding:20px 10px}}}}@media(max-width:480px){{.metrics{{grid-template-columns:1fr}}}}{FAQ_CSS}</style><script src="/site-auth-nav.js?v=5"></script></head><body>
<nav><div><strong>Extreme Trading Inc.</strong></div><div><a href="index.html">Home</a><a href="strategies.html">Strategies</a><a href="subscribe.html">Subscribe</a><a href="members.html">Login</a><a href="about.html">About</a><a href="contact.html">Contact</a></div></nav><main class="container">
<section class="hero"><div class="eyebrow">Backtested tactical ETF allocation model</div><h1>MoMoEtf2</h1><p>Tactical asset allocation model that adjusts monthly across major market exposures using proprietary market-environment and risk-management signals. Subscribers receive current model allocations and update alerts.</p><p class="subtle">Backtest period: {start_date} through {end_date} · Starting equity: {currency(start_equity)}</p>{render_faq("momentum2", audience)}</section>
<section class="metrics">{metrics_html}</section>
{before_results}
<section class="panel"><h2>Equity Curve</h2><p class="subtle">MoMoEtf2 and SPY equity with drawdowns through {end_date}.</p><div class="chart">{chart_html}</div></section>
<section class="panel enlarged-table"><h2>Monthly Returns</h2>{build_monthly_table(monthly, daily)}</section>
{after_results}
<section class="panel disclaimer"><strong>Important:</strong> These are simulated backtest results, not verified live performance. Backtests are hypothetical, may benefit from hindsight, and may not reflect transaction costs, slippage, liquidity constraints, taxes, or future market conditions. Past or simulated performance does not guarantee future results.</section>
</main><footer>&copy; 2026 Extreme Trading Inc.</footer></body></html>"""
    if audience == "public":
        forbidden = ("id=\"current-month\"", "<h2>Latest Alert</h2>", "<h2>Latest 20 Historical Trades</h2>")
        leaked = [item for item in forbidden if item and item in page]
        if leaked:
            raise RuntimeError(f"Public Momentum ETF2 page contains member-only content: {leaked}")
    return page


def main():
    args = parse_args()
    page = render(args.source, args.audience, args.chart_src)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")
    summary = pd.read_csv(args.source / "summary.csv", index_col=0)
    strategy = summary.iloc[:, 0]
    spy = summary.iloc[:, 1]
    update_backtest_card(
        args.strategies_page,
        "MoMoEtf2",
        strategy["CAGR"],
        strategy["Sharpe"],
        strategy["Daily max drawdown"],
        spy["Daily max drawdown"],
    )
    update_member_backtest_card(
        args.members_page,
        "MoMoEtf2",
        strategy["CAGR"],
        strategy["Sharpe"],
        strategy["Daily max drawdown"],
        spy["Daily max drawdown"],
    )
    print(f"Generated {args.audience} {args.output} from {args.source}")


if __name__ == "__main__":
    main()
