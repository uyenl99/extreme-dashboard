import argparse
import html
import json
from pathlib import Path

import pandas as pd

from generate_momentum_page import build_position_calculator


REQUIRED_FILES = (
    "summary.csv",
    "daily_drawdown.csv",
    "monthly_pnl_by_year.csv",
    "latest_alert.json",
)

FAQ_CSS = """
.faq-wrap{margin:14px 0 0}.faq-wrap>summary{display:inline-flex;align-items:center;gap:8px;cursor:pointer;list-style:none;background:#2563eb;color:#fff;border:1px solid #60a5fa;border-radius:8px;padding:10px 16px;font-weight:700}.faq-wrap>summary::-webkit-details-marker{display:none}.faq-wrap>summary:after{content:'+';font-size:18px}.faq-wrap[open]>summary:after{content:'-'}.faq-content{margin-top:14px;padding:4px 18px;background:#0f172a;border:1px solid #374151;border-radius:10px}.faq-content details{padding:14px 0;border-bottom:1px solid #273449}.faq-content details:last-child{border-bottom:0}.faq-content details summary{cursor:pointer;font-weight:700;color:#e5e7eb}.faq-content details p{color:#cbd5e1;line-height:1.6;margin:10px 0 2px}.faq-note{color:#94a3b8;font-size:13px;margin:14px 0}
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Generate the public MoMoEtf2 results page.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("inflation-compass"),
        help="Directory containing copied MoMoEtf2 output files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("momentum2.html"),
        help="HTML file to generate.",
    )
    parser.add_argument(
        "--start-equity",
        type=float,
        default=100000.0,
        help="Starting equity displayed in the chart and metrics.",
    )
    return parser.parse_args()


def metric_class(value):
    text = str(value).strip()
    if text.startswith("-"):
        return "negative"
    if text and text not in ("0", "0.0", "0.00", "0.00%"):
        return "positive"
    return "muted"


def pct(value, decimals=2):
    return f"{float(value) * 100:,.{decimals}f}%"


def currency(value):
    return f"${float(value):,.0f}"


def render_faq():
    return (
        '<details class="faq-wrap"><summary aria-label="Open Strategy FAQ">Strategy FAQ</summary>'
        '<div class="faq-content"><p class="faq-note">Public overview. Current allocations and detailed signal logic are not shown here.</p>'
        '<details><summary>What is MoMoEtf2?</summary>'
        '<p>MoMoEtf2 is a tactical ETF allocation model. It adjusts monthly across major market exposures using proprietary market-environment and risk-management signals.</p></details>'
        '<details><summary>How often can holdings change?</summary>'
        '<p>The model is designed around a monthly update process. It is not an intraday trading system, and an allocation can remain unchanged for multiple months.</p></details>'
        '<details><summary>Are the charts live account results?</summary>'
        '<p>No. They are simulated backtest results and may omit real-world costs, taxes, slippage, and execution differences.</p></details>'
        '<details><summary>What is available to members?</summary>'
        '<p>Members receive current model allocation details, model alerts, and subscriber-only updates.</p></details>'
        '</div></details>'
    )


def load_results(source, start_equity):
    missing = [name for name in REQUIRED_FILES if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required MoMoEtf2 output files: {', '.join(missing)}")

    summary_raw = pd.read_csv(source / "summary.csv", index_col=0)
    daily_raw = pd.read_csv(source / "daily_drawdown.csv", parse_dates=["Date"])
    monthly = pd.read_csv(source / "monthly_pnl_by_year.csv")
    alert = json.loads((source / "latest_alert.json").read_text(encoding="utf-8"))

    daily = pd.DataFrame(
        {
            "Date": daily_raw["Date"],
            "Equity": daily_raw["strategy_wealth"].astype(float) * start_equity,
            "SPY_Equity": daily_raw["spy_wealth"].astype(float) * start_equity,
        }
    ).dropna()

    if daily["Date"].isna().any() or not daily["Date"].is_monotonic_increasing:
        raise ValueError("daily_drawdown.csv dates must be valid and sorted")

    summary = {
        "cagr": float(summary_raw.loc["CAGR", "Inflation Compass"]),
        "spy_cagr": float(summary_raw.loc["CAGR", "SPY"]),
        "sharpe": float(summary_raw.loc["Sharpe", "Inflation Compass"]),
        "max_drawdown": float(summary_raw.loc["Daily max drawdown", "Inflation Compass"]),
        "spy_max_drawdown": float(summary_raw.loc["Daily max drawdown", "SPY"]),
        "total_return": float(summary_raw.loc["Growth of $1", "Inflation Compass"]) - 1,
        "final_equity": float(summary_raw.loc["Growth of $1", "Inflation Compass"]) * start_equity,
    }
    active_months = int(monthly[["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]].count(axis=1).sum())
    return summary, daily, monthly, active_months, alert


def build_chart(daily):
    dates = [value.isoformat() for value in daily["Date"]]
    strategy = [round(float(value), 2) for value in daily["Equity"]]
    spy = [round(float(value), 2) for value in daily["SPY_Equity"]]
    traces = [
        {
            "x": dates,
            "y": strategy,
            "mode": "lines",
            "name": "MoMoEtf2",
            "line": {"color": "#60a5fa", "width": 3},
            "type": "scatter",
        },
        {
            "x": dates,
            "y": spy,
            "mode": "lines",
            "name": "SPY",
            "line": {"color": "#94a3b8", "width": 1.7},
            "type": "scatter",
        },
    ]
    layout = {
        "template": "plotly_dark",
        "height": 520,
        "margin": {"l": 55, "r": 25, "t": 25, "b": 45},
        "paper_bgcolor": "#111827",
        "plot_bgcolor": "#111827",
        "hovermode": "x unified",
        "legend": {"orientation": "h", "y": 1.08, "x": 0},
        "yaxis": {
            "title": {"text": "Equity ($)"},
            "tickprefix": "$",
            "tickformat": ",.0f",
            "gridcolor": "#273449",
        },
        "xaxis": {"gridcolor": "#273449"},
    }
    return (
        '<div style="height:520px; width:100%;">'
        '<script>window.PlotlyConfig = {MathJaxConfig: "local"};</script>'
        '<script charset="utf-8" src="https://cdn.plot.ly/plotly-3.7.0.min.js" '
        'integrity="sha256-jvTGqxNp8AGWEcvNLVuKr+8j5dGe9Yw51LQkmDH+IYA=" '
        'crossorigin="anonymous"></script>'
        '<div id="momoetf2-equity-chart" class="plotly-graph-div" style="height:100%; width:100%;"></div>'
        "<script>"
        "window.PLOTLYENV=window.PLOTLYENV || {};"
        'if (document.getElementById("momoetf2-equity-chart")) {'
        'Plotly.newPlot("momoetf2-equity-chart",'
        f"{json.dumps(traces, separators=(',', ':'))},"
        f"{json.dumps(layout, separators=(',', ':'))},"
        '{"responsive":true});'
        "}"
        "</script></div>"
    )


def build_monthly_table(monthly):
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    headers = "".join(f"<th>{name}</th>" for name in month_names + ["Year Return"])
    rows = []
    for item in monthly.sort_values("Year", ascending=False).itertuples(index=False):
        values = [getattr(item, name) for name in month_names]
        values.append(getattr(item, "_13"))
        cells = []
        for value in values:
            if pd.isna(value) or value == "":
                cells.append('<td class="muted">—</td>')
            else:
                css = "positive" if float(value) > 0 else "negative" if float(value) < 0 else "muted"
                cells.append(f'<td class="{css}">{float(value) * 100:.1f}%</td>')
        rows.append(f"<tr><th>{int(item.Year)}</th>{''.join(cells)}</tr>")
    return (
        '<div class="table-wrap"><table><thead><tr><th>Year</th>'
        f'{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_page(summary, daily, monthly, active_months, start_equity, alert):
    chart_html = build_chart(daily)
    start_date = daily["Date"].min().strftime("%Y-%m-%d")
    end_date = daily["Date"].max().strftime("%Y-%m-%d")
    metrics = (
        ("Strategy CAGR", pct(summary["cagr"])),
        ("Strategy Max Drawdown", pct(summary["max_drawdown"])),
        ("Total Return", pct(summary["total_return"])),
        ("Sharpe Ratio", f'{summary["sharpe"]:.2f}'),
        ("SPY CAGR", pct(summary["spy_cagr"])),
        ("SPY Max Drawdown", pct(summary["spy_max_drawdown"])),
        ("Final Equity", currency(summary["final_equity"])),
        ("Active Months", f"{active_months:,}"),
    )
    metric_html = "".join(
        f'<div class="metric"><div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value {metric_class(value)}">{html.escape(value)}</div></div>'
        for label, value in metrics
    )
    member_sections = (
        '<section class="panel"><h2>Member Signals</h2>'
        '<p class="subtle">Current allocation details, latest alerts, and recent model updates are available to members.</p>'
        '<p><a href="subscribe.html">View membership options</a></p>'
        + build_position_calculator(
            [alert.get("next_holding") or alert.get("current_holding")],
            "momoetf2-position-calculator",
        )
        + '</section>'
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MoMoEtf2 Backtest - Extreme Trading Inc.</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial,Helvetica,sans-serif}} nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 30px;background:#111827}} nav a{{color:white;text-decoration:none;margin-left:20px}} .container{{width:95%;max-width:1400px;margin:auto;padding:30px 20px 60px}} .hero,.panel{{background:#111827;border:1px solid #374151;border-radius:12px;padding:26px;margin-bottom:22px}} .eyebrow{{color:#60a5fa;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:bold}} h1{{margin:8px 0 10px}} h2{{margin-top:0}} .subtle,.muted{{color:#94a3b8}} .metrics{{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:14px;margin:22px 0}} .metric{{background:#111827;border:1px solid #374151;border-radius:10px;padding:18px}} .metric-label{{color:#94a3b8;font-size:13px}} .metric-value{{font-size:24px;font-weight:700;margin-top:6px}} .chart{{overflow:hidden}} .table-wrap{{overflow-x:auto}} table{{width:100%;border-collapse:collapse;background:#111827}} th,td{{border:1px solid #374151;padding:7px 9px;text-align:right;font-size:12px;white-space:nowrap}} th{{background:#1f2937;color:white}} th:first-child,td:first-child{{text-align:left}} .positive{{color:#22c55e;font-weight:600}} .negative{{color:#f87171;font-weight:600}} .compact{{max-width:420px}} .regime{{font-weight:700}} .risk-on{{color:#60a5fa}} .risk-off{{color:#f59e0b}} .disclaimer{{font-size:13px;line-height:1.6;color:#94a3b8}} footer{{text-align:center;padding:30px;color:#94a3b8}} @media(max-width:800px){{nav{{align-items:flex-start;padding:16px;gap:12px}}nav div:last-child{{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}}nav a{{margin-left:8px;font-size:12px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.container{{padding:20px 10px}}}} @media(max-width:480px){{.metrics{{grid-template-columns:1fr}}}}
{FAQ_CSS}</style>
<script>
  window.va = window.va || function () {{ (window.vaq = window.vaq || []).push(arguments); }};
</script>
<script defer src="/_vercel/insights/script.js"></script>
</head>
<body>
<nav><div><strong>Extreme Trading Inc.</strong></div><div><a href="index.html">Home</a><a href="subscribe.html">Subscribe</a><a href="members.html">Login</a></div></nav>
<main class="container">
<section class="hero"><div class="eyebrow">Backtested tactical ETF allocation model</div><h1>MoMoEtf2</h1><p>Tactical asset allocation model that adjusts monthly across major market exposures using proprietary market-environment and risk-management signals. Subscribers receive current model allocations and update alerts.</p><p class="subtle">Backtest period: {start_date} through {end_date} · Starting equity: {currency(start_equity)}</p>{render_faq()}</section>
<section class="metrics">{metric_html}</section>
<section class="panel"><h2>Equity Curve</h2><p class="subtle">MoMoEtf2 compared with an equal-starting-equity SPY benchmark.</p><div class="chart">{chart_html}</div></section>
<section class="panel"><h2>Monthly Returns</h2>{build_monthly_table(monthly)}</section>
{member_sections}
<section class="panel disclaimer"><strong>Important:</strong> These are simulated backtest results, not verified live performance. Backtests are hypothetical, may benefit from hindsight, and may not reflect transaction costs, slippage, liquidity constraints, taxes, or future market conditions. Past or simulated performance does not guarantee future results.</section>
</main>
<footer>© 2026 Extreme Trading Inc.</footer>
</body>
</html>"""


def main():
    args = parse_args()
    summary, daily, monthly, active_months, alert = load_results(args.source, args.start_equity)
    args.output.write_text(
        render_page(summary, daily, monthly, active_months, args.start_equity, alert),
        encoding="utf-8",
    )
    print(f"Generated {args.output} from {args.source}")


if __name__ == "__main__":
    main()
