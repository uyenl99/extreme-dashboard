import argparse
import html
import json
from pathlib import Path

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Momentum ETF2 public or member page.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audience", choices=("public", "member"), default="public")
    parser.add_argument("--chart-src", default="inflation-compass/wealth.png")
    return parser.parse_args()


def pct(value):
    return f"{float(value) * 100:.2f}%"


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


def allocation_history(monthly_backtest, limit=50):
    data = monthly_backtest.copy()
    data.index = pd.PeriodIndex(data.index.astype(str), freq="M")
    display = pd.DataFrame(index=data.index)
    display["Month"] = data.index.astype(str)
    display["Holdings"] = data["held"]
    display["Regime"] = data["signal_regime"].shift(1).str.replace("_", " ").str.title()
    display["Return"] = data["strategy_return"]
    display["SPY"] = data["spy_return"]
    return display.sort_index(ascending=False).head(limit).reset_index(drop=True)


def current_month_panel(monthly_backtest, daily):
    latest_day = pd.to_datetime(daily.index).max()
    current_period = latest_day.to_period("M")
    row = monthly_backtest.loc[str(current_period)]
    holding = str(row["held"])
    regime = str(monthly_backtest["signal_regime"].shift(1).loc[str(current_period)])
    month_return = float(row["strategy_return"])
    return_class = "positive" if month_return > 0 else "negative" if month_return < 0 else "muted"
    return (
        '<section class="panel" id="current-month"><h2>Current Partial Month</h2>'
        f'<p class="subtle">Mark-to-market through {latest_day:%Y-%m-%d}; this is an incomplete-month estimate.</p>'
        '<div class="metrics">'
        f'<div class="metric"><div class="metric-label">Current Month Return</div><div class="metric-value {return_class}">{pct(month_return)}</div></div>'
        f'<div class="metric"><div class="metric-label">Holding</div><div class="metric-value positive">{html.escape(holding)}</div></div>'
        f'<div class="metric"><div class="metric-label">Regime</div><div class="metric-value">{html.escape(regime.upper())}</div></div>'
        f'<div class="metric"><div class="metric-label">Effective Month</div><div class="metric-value">{current_period}</div></div>'
        '</div></section>'
    )


def latest_alert_table(alert):
    frame = pd.DataFrame([{
        "Signal": alert["signal_month_end"],
        "Regime": str(alert["regime"]).replace("_", " ").upper(),
        "Holding": alert["next_holding"],
        "Execution": f'{alert["effective_month"]} open',
        "Changed": "Yes" if alert["allocation_changed"] else "No",
    }])
    return table(frame)


def render(source, audience, chart_src):
    summary = pd.read_csv(source / "summary.csv", index_col=0)
    monthly = pd.read_csv(source / "monthly_pnl_by_year.csv").sort_values("Year", ascending=False)
    monthly_backtest = pd.read_csv(source / "monthly_backtest.csv", index_col=0)
    daily = pd.read_csv(source / "daily_drawdown.csv", index_col=0, parse_dates=True)
    alert = json.loads((source / "latest_alert.json").read_text(encoding="utf-8"))
    strategy = summary.iloc[:, 0]
    spy = summary.iloc[:, 1]
    metrics = (
        ("Strategy CAGR", pct(strategy["CAGR"])),
        ("Strategy Max Drawdown", pct(strategy["Daily max drawdown"])),
        ("Sharpe Ratio", f'{float(strategy["Sharpe"]):.2f}'),
        ("Growth of $1", f'${float(strategy["Growth of $1"]):.2f}'),
        ("SPY CAGR", pct(spy["CAGR"])),
        ("SPY Max Drawdown", pct(spy["Daily max drawdown"])),
    )
    metrics_html = "".join(
        f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>'
        for label, value in metrics
    )
    if audience == "member":
        allocations = allocation_history(monthly_backtest)
        protected = (
            current_month_panel(monthly_backtest, daily)
            + '<section class="panel"><h2>Latest Alert</h2>'
            + latest_alert_table(alert)
            + '</section>'
            + '<section class="panel"><h2>Recent Monthly Allocations</h2>'
            + table(allocations, ("Return", "SPY"))
            + '</section>'
        )
    else:
        protected = (
            '<section class="panel"><h2>Member Signals</h2><p class="subtle">Current allocation and recent allocation changes are available to members.</p>'
            '<p><a href="subscribe.html">View membership options</a></p></section>'
        )
    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Momentum ETF2 - Extreme Trading Inc.</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial,Helvetica,sans-serif}}nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 30px;background:#111827}}nav a{{color:white;text-decoration:none;margin-left:20px}}a{{color:#60a5fa}}.container{{width:95%;max-width:1400px;margin:auto;padding:30px 20px 60px}}.hero,.panel{{background:#111827;border:1px solid #374151;border-radius:12px;padding:26px;margin-bottom:22px}}.eyebrow{{color:#60a5fa;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:bold}}h1{{margin:8px 0 10px}}h2{{margin-top:0}}.subtle,.muted{{color:#94a3b8}}.metrics{{display:grid;grid-template-columns:repeat(3,minmax(160px,1fr));gap:14px;margin:22px 0}}.metric{{background:#111827;border:1px solid #374151;border-radius:10px;padding:18px}}.metric-label{{color:#94a3b8;font-size:13px}}.metric-value{{font-size:24px;font-weight:700;margin-top:6px}}.positive{{color:#22c55e}}.negative{{color:#f87171}}.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #374151;padding:7px 9px;text-align:right;font-size:12px;white-space:nowrap}}th{{background:#1f2937}}th:first-child,td:first-child{{text-align:left}}.chart img{{width:100%;display:block;border-radius:8px}}footer{{text-align:center;padding:30px;color:#94a3b8}}</style></head><body>
<nav><div><strong>Extreme Trading Inc.</strong></div><div><a href="index.html">Home</a><a href="subscribe.html">Subscribe</a><a href="members.html">Login</a></div></nav><main class="container">
<section class="hero"><div class="eyebrow">Market regime ETF rotation</div><h1>Momentum ETF2</h1><p>Inflation Compass rotates monthly among XLE, XLK, XLU, or a 50/50 XLP/IEF allocation according to market growth and inflation expectations.</p></section>
<section class="metrics">{metrics_html}</section>{protected}
<section class="panel chart"><h2>Equity Curve</h2><img src="{html.escape(chart_src)}" alt="Inflation Compass equity curve"></section>
<section class="panel"><h2>Monthly Returns</h2>{table(monthly, tuple(monthly.columns[1:]))}</section>
</main><footer>&copy; 2026 Extreme Trading Inc.</footer></body></html>"""
    if audience == "public":
        forbidden = ("id=\"current-month\"", "<h2>Latest Alert</h2>", "<h2>Recent Monthly Allocations</h2>")
        leaked = [item for item in forbidden if item and item in page]
        if leaked:
            raise RuntimeError(f"Public Momentum ETF2 page contains member-only content: {leaked}")
    return page


def main():
    args = parse_args()
    page = render(args.source, args.audience, args.chart_src)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")
    print(f"Generated {args.audience} {args.output} from {args.source}")


if __name__ == "__main__":
    main()
