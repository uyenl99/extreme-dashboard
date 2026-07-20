import argparse
import html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


REQUIRED_FILES = (
    "summary_stats.csv",
    "equity_curve.csv",
    "benchmark_curve.csv",
    "monthly_returns.csv",
    "yearly_returns.csv",
    "trades.csv",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate the public Mean Reversion backtest page."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("../RevMurphy/output_long_short"),
        help="Directory containing the RevMurphy output CSV files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("mean-reversion.html"),
        help="HTML file to generate.",
    )
    return parser.parse_args()


def load_results(source):
    missing = [name for name in REQUIRED_FILES if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing required RevMurphy output files: {', '.join(missing)}"
        )

    summary = pd.read_csv(source / "summary_stats.csv")
    if len(summary) != 1:
        raise ValueError("summary_stats.csv must contain exactly one result row")

    equity = pd.read_csv(source / "equity_curve.csv", parse_dates=["date"])
    benchmarks = pd.read_csv(source / "benchmark_curve.csv", parse_dates=["date"])
    monthly = pd.read_csv(source / "monthly_returns.csv")
    yearly = pd.read_csv(source / "yearly_returns.csv")
    trades = pd.read_csv(source / "trades.csv")

    for frame, label in ((equity, "equity_curve"), (benchmarks, "benchmark_curve")):
        if frame["date"].isna().any() or not frame["date"].is_monotonic_increasing:
            raise ValueError(f"{label}.csv dates must be valid and sorted")

    return summary.iloc[0], equity, benchmarks, monthly, yearly, trades


def pct(value, decimals=2):
    return f"{float(value) * 100:,.{decimals}f}%"


def build_chart(equity, benchmarks):
    chart = equity[["date", "equity"]].merge(benchmarks, on="date", how="left")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart["date"],
            y=chart["equity"],
            mode="lines",
            name="Mean Reversion",
            line=dict(color="#60a5fa", width=3),
        )
    )
    colors = {"SPY_equity": "#94a3b8", "QQQ_equity": "#a78bfa", "VOO_equity": "#34d399"}
    for column, color in colors.items():
        if column in chart:
            fig.add_trace(
                go.Scatter(
                    x=chart["date"],
                    y=chart[column],
                    mode="lines",
                    name=column.replace("_equity", ""),
                    line=dict(color=color, width=1.5),
                    visible="legendonly",
                )
            )
    fig.update_layout(
        template="plotly_dark",
        height=520,
        margin=dict(l=55, r=25, t=25, b=45),
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis_title="Equity ($)",
    )
    fig.update_yaxes(tickprefix="$", tickformat=",.0f", gridcolor="#273449")
    fig.update_xaxes(gridcolor="#273449")
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"responsive": True},
        div_id="mean-reversion-equity-chart",
    )


def build_monthly_table(monthly):
    data = monthly.copy()
    data["year"] = data["month"].astype(str).str[:4].astype(int)
    data["month_number"] = data["month"].astype(str).str[5:7].astype(int)
    pivot = data.pivot(index="year", columns="month_number", values="return_pct")
    pivot["YTD"] = pivot.apply(
        lambda row: ((1 + row.dropna()).prod() - 1), axis=1
    )
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    columns = list(range(1, 13)) + ["YTD"]
    head = "".join(f"<th>{label}</th>" for label in labels + ["YTD"])
    rows = []
    for year, row in pivot.sort_index(ascending=False).iterrows():
        cells = []
        for column in columns:
            value = row.get(column)
            if pd.isna(value):
                cells.append("<td class=\"muted\">—</td>")
            else:
                css = "positive" if value > 0 else "negative" if value < 0 else "muted"
                cells.append(f'<td class="{css}">{value * 100:.1f}%</td>')
        rows.append(f"<tr><th>{year}</th>{''.join(cells)}</tr>")
    return f'<div class="table-wrap"><table><thead><tr><th>Year</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def build_yearly_table(yearly):
    rows = []
    for item in yearly.sort_values("year", ascending=False).itertuples(index=False):
        css = "positive" if item.return_pct > 0 else "negative" if item.return_pct < 0 else "muted"
        rows.append(
            f'<tr><td>{int(item.year)}</td><td>{html.escape(str(item.start_date))}</td>'
            f'<td>{html.escape(str(item.end_date))}</td><td class="{css}">{item.return_pct * 100:.2f}%</td></tr>'
        )
    return f'<div class="table-wrap compact"><table><thead><tr><th>Year</th><th>Start</th><th>End</th><th>Return</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def build_trade_table(trades, limit=50):
    closed = trades[trades["status"].astype(str).str.lower() == "closed"].copy()
    closed["exit_date"] = pd.to_datetime(closed["exit_date"], errors="coerce")
    closed = closed.sort_values("exit_date", ascending=False).head(limit)
    rows = []
    for item in closed.itertuples(index=False):
        css = "positive" if item.pnl_dollars >= 0 else "negative"
        side_css = "long" if str(item.side).lower() == "long" else "short"
        rows.append(
            f"<tr><td>{html.escape(str(item.ticker))}</td>"
            f'<td><span class="side {side_css}">{html.escape(str(item.side).title())}</span></td>'
            f"<td>{html.escape(str(item.entry_date))}</td><td>{html.escape(str(item.exit_date.date()))}</td>"
            f"<td>{float(item.holding_days):.0f}</td>"
            f'<td class="{css}">${float(item.pnl_dollars):,.0f}</td>'
            f'<td class="{css}">{float(item.return_pct) * 100:.2f}%</td></tr>'
        )
    return f'<div class="table-wrap"><table><thead><tr><th>Ticker</th><th>Side</th><th>Entry</th><th>Exit</th><th>Days</th><th>P/L</th><th>Return</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def render_page(summary, equity, benchmarks, monthly, yearly, trades):
    chart_html = build_chart(equity, benchmarks)
    metrics = (
        ("Total Return", pct(summary.total_return)),
        ("CAGR", pct(summary.cagr)),
        ("Sharpe Ratio", f"{summary.annualized_sharpe:.2f}"),
        ("Max Drawdown", pct(summary.max_drawdown)),
        ("Win Rate", pct(summary.win_rate)),
        ("Closed Trades", f"{int(summary.trades):,}"),
        ("Average Trade", pct(summary.avg_trade_return)),
        ("Final Equity", f"${summary.final_equity:,.0f}"),
    )
    metric_html = "".join(
        f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>'
        for label, value in metrics
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mean Reversion Backtest - Extreme Trading Inc.</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial,Helvetica,sans-serif}} nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 30px;background:#111827}} nav a{{color:white;text-decoration:none;margin-left:20px}} .container{{width:95%;max-width:1400px;margin:auto;padding:30px 20px 60px}} .hero,.panel{{background:#111827;border:1px solid #374151;border-radius:12px;padding:26px;margin-bottom:22px}} .eyebrow{{color:#60a5fa;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:bold}} h1{{margin:8px 0 10px}} h2{{margin-top:0}} .subtle,.muted{{color:#94a3b8}} .metrics{{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:14px;margin:22px 0}} .metric{{background:#111827;border:1px solid #374151;border-radius:10px;padding:18px}} .metric-label{{color:#94a3b8;font-size:13px}} .metric-value{{font-size:24px;font-weight:700;margin-top:6px}} .chart{{overflow:hidden}} .table-wrap{{overflow-x:auto}} table{{width:100%;border-collapse:collapse;background:#111827}} th,td{{border:1px solid #374151;padding:7px 9px;text-align:right;font-size:12px;white-space:nowrap}} th{{background:#1f2937;color:white}} th:first-child,td:first-child{{text-align:left}} .positive{{color:#22c55e;font-weight:600}} .negative{{color:#f87171;font-weight:600}} .compact{{max-width:680px}} .side{{font-weight:700}} .side.long{{color:#60a5fa}} .side.short{{color:#f59e0b}} .disclaimer{{font-size:13px;line-height:1.6;color:#94a3b8}} footer{{text-align:center;padding:30px;color:#94a3b8}} @media(max-width:800px){{nav{{align-items:flex-start;padding:16px;gap:12px}}nav div:last-child{{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}}nav a{{margin-left:8px;font-size:12px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.container{{padding:20px 10px}}}} @media(max-width:480px){{.metrics{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<nav><div><strong>Extreme Trading Inc.</strong></div><div><a href="index.html">Home</a><a href="performance.html">Performance</a><a href="strategies.html">Strategies</a><a href="subscribe.html">Subscribe</a><a href="members.html">Members</a></div></nav>
<main class="container">
<section class="hero"><div class="eyebrow">Backtested long/short strategy</div><h1>Mean Reversion</h1><p>Systematic equity strategy seeking short-term price dislocations and subsequent reversion while managing long and short exposure.</p><p class="subtle">Backtest period: {summary.start_date} through {summary.end_date} · Starting equity: ${equity.iloc[0]['equity']:,.0f}</p></section>
<section class="metrics">{metric_html}</section>
<section class="panel"><h2>Equity Curve</h2><p class="subtle">Select SPY, QQQ, or VOO in the legend to add benchmark comparisons.</p><div class="chart">{chart_html}</div></section>
<section class="panel"><h2>Monthly Returns</h2>{build_monthly_table(monthly)}</section>
<section class="panel"><h2>Yearly Returns</h2>{build_yearly_table(yearly)}</section>
<section class="panel"><h2>Recent Closed Trades</h2>{build_trade_table(trades)}</section>
<section class="panel disclaimer"><strong>Important:</strong> These are simulated backtest results, not verified live performance. Backtests are hypothetical, may benefit from hindsight, and may not reflect transaction costs, slippage, liquidity constraints, taxes, or future market conditions. Past or simulated performance does not guarantee future results.</section>
</main>
<footer>© 2026 Extreme Trading Inc.</footer>
</body>
</html>"""


def main():
    args = parse_args()
    summary, equity, benchmarks, monthly, yearly, trades = load_results(args.source)
    args.output.write_text(
        render_page(summary, equity, benchmarks, monthly, yearly, trades),
        encoding="utf-8",
    )
    print(f"Generated {args.output} from {args.source}")


if __name__ == "__main__":
    main()
