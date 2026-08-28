import argparse
import html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


REQUIRED_FILES = (
    "summary.csv",
    "daily_equity_entries_exits.csv",
    "dual_momentum_results.csv",
    "monthly_return_table.csv",
    "next_entry_alert.txt",
)

FAQ_CSS = """
.faq-wrap{margin:14px 0 0}.faq-wrap>summary{display:inline-flex;align-items:center;gap:8px;cursor:pointer;list-style:none;background:#2563eb;color:#fff;border:1px solid #60a5fa;border-radius:8px;padding:10px 16px;font-weight:700}.faq-wrap>summary::-webkit-details-marker{display:none}.faq-wrap>summary:after{content:'+';font-size:18px}.faq-wrap[open]>summary:after{content:'-'}.faq-content{margin-top:14px;padding:4px 18px;background:#0f172a;border:1px solid #374151;border-radius:10px}.faq-content details{padding:14px 0;border-bottom:1px solid #273449}.faq-content details:last-child{border-bottom:0}.faq-content details summary{cursor:pointer;font-weight:700;color:#e5e7eb}.faq-content details p{color:#cbd5e1;line-height:1.6;margin:10px 0 2px}.faq-note{color:#94a3b8;font-size:13px;margin:14px 0}
"""


def metric_class(value):
    text = str(value).strip()
    if text.startswith("-"):
        return "negative"
    if text and text != "0" and text != "0.00":
        return "positive"
    return "muted"


def render_faq():
    return (
        '<details class="faq-wrap"><summary aria-label="Open Strategy FAQ">Strategy FAQ</summary>'
        '<div class="faq-content"><p class="faq-note">Public overview. Current signals and positions are not shown here.</p>'
        '<details><summary>What is MoMoEtf1?</summary>'
        '<p>MoMoEtf1 is a systematic ETF allocation model. It adjusts monthly across major market exposures using proprietary trend and risk-management signals.</p></details>'
        '<details><summary>How often can holdings change?</summary>'
        '<p>The model is designed around a monthly update process. It is not an intraday trading system, and an allocation can remain unchanged for multiple months.</p></details>'
        '<details><summary>Are the charts live account results?</summary>'
        '<p>No. They are simulated backtest results and may omit real-world costs, taxes, slippage, and execution differences.</p></details>'
        '<details><summary>What is available to members?</summary>'
        '<p>Members receive current model allocation details, model alerts, and subscriber-only updates.</p></details>'
        '</div></details>'
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate the public MoMoEtf1 backtest page."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("../DualMom/output_momo5"),
        help="Directory containing the momo5 output files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("momentum.html"),
        help="HTML file to generate.",
    )
    return parser.parse_args()


def load_results(source):
    missing = [name for name in REQUIRED_FILES if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing required momo5 output files: {', '.join(missing)}"
        )

    summary = pd.read_csv(source / "summary.csv")
    if len(summary) != 1:
        raise ValueError("summary.csv must contain exactly one result row")

    daily = pd.read_csv(
        source / "daily_equity_entries_exits.csv", parse_dates=["Date"]
    )
    allocations = pd.read_csv(
        source / "dual_momentum_results.csv",
        parse_dates=["date", "exit_date"],
    )
    monthly = pd.read_csv(source / "monthly_return_table.csv")
    partial_path = source / "partial_month_return.csv"
    partial = pd.read_csv(partial_path).iloc[0] if partial_path.is_file() else None

    for frame, column, label in (
        (daily, "Date", "daily_equity_entries_exits"),
        (allocations, "date", "dual_momentum_results"),
    ):
        if frame[column].isna().any() or not frame[column].is_monotonic_increasing:
            raise ValueError(f"{label}.csv dates must be valid and sorted")

    alert = parse_alert(source / "next_entry_alert.txt")
    return summary.iloc[0], daily, allocations, monthly, alert, partial


def pct(value, decimals=2):
    return f"{float(value) * 100:,.{decimals}f}%"


def parse_alert(path):
    aliases = {
        "signal month": "Signal",
        "signal date": "Signal",
        "execute at": "Execution",
        "execution": "Execution",
        "holdings": "Holdings",
    }
    alert = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        label, value = (part.strip() for part in line.split(":", 1))
        canonical = aliases.get(label.lower())
        if canonical:
            alert[canonical] = value
    return alert


def build_alert_table(alert):
    columns = ("Signal", "Execution", "Member Detail")
    headers = "".join(f"<th>{column}</th>" for column in columns)
    cells = []
    for column in columns:
        value = "Available to subscribers" if column == "Member Detail" else alert.get(column, "—")
        cells.append(f"<td>{html.escape(value)}</td>")
    return f'<div class="table-wrap"><table><thead><tr>{headers}</tr></thead><tbody><tr>{"".join(cells)}</tr></tbody></table></div>'


def build_position_calculator(positions, calculator_id):
    positions = [str(position).strip() for position in positions if str(position).strip()]
    if not positions:
        return ""
    weight = 1 / len(positions)
    rows = "".join(
        f'<tr data-weight="{weight:.12f}"><td>{html.escape(position)}</td>'
        f'<td>{weight * 100:.2f}%</td><td class="calculated-size">—</td></tr>'
        for position in positions
    )
    return f"""
<style>
#{calculator_id}-actions{{margin-top:16px}} #{calculator_id}-toggle{{border:0;border-radius:7px;background:#2563eb;color:white;padding:10px 15px;font:inherit;font-weight:700;cursor:pointer}} #{calculator_id}{{margin-top:18px;padding-top:18px;border-top:1px solid #374151}} #{calculator_id} label{{display:block;margin-bottom:7px;color:#cbd5e1;font-size:13px}} #{calculator_id}-equity{{width:min(100%,320px);border:1px solid #4b5563;border-radius:7px;background:#0f172a;color:#e5e7eb;padding:10px 12px;font:inherit}} #{calculator_id}-error{{min-height:20px;margin:7px 0;color:#f87171;font-size:13px}}
</style>
<div id="{calculator_id}-actions"><button type="button" id="{calculator_id}-toggle" aria-expanded="false" aria-controls="{calculator_id}">Calculate Position Size</button></div>
<div id="{calculator_id}" hidden><label for="{calculator_id}-equity">Your account equity</label><input id="{calculator_id}-equity" type="number" min="0.01" step="1000" inputmode="decimal" placeholder="100,000"><p id="{calculator_id}-error" role="alert"></p><div class="table-wrap"><table><thead><tr><th>Ticker</th><th>Target Weight</th><th>Your Position Size</th></tr></thead><tbody>{rows}</tbody></table></div><p class="subtle">Dollar targets are equally allocated across the current model holdings. They do not calculate share quantity or account for execution costs.</p></div>
<script>(()=>{{const box=document.getElementById("{calculator_id}"),button=document.getElementById("{calculator_id}-toggle"),input=document.getElementById("{calculator_id}-equity"),error=document.getElementById("{calculator_id}-error"),rows=Array.from(box.querySelectorAll("tbody tr")),money=new Intl.NumberFormat("en-US",{{style:"currency",currency:"USD",maximumFractionDigits:2}});function calculate(){{const equity=Number(input.value),valid=Number.isFinite(equity)&&equity>0;error.textContent=valid||!input.value?"":"Enter an account equity greater than zero.";rows.forEach(row=>row.querySelector(".calculated-size").textContent=valid?money.format(equity*Number(row.dataset.weight)):"—")}}button.addEventListener("click",()=>{{const opening=box.hidden;box.hidden=!opening;button.setAttribute("aria-expanded",String(opening));button.textContent=opening?"Hide Position Calculator":"Calculate Position Size";if(opening)input.focus()}});input.addEventListener("input",calculate)}})();</script>"""


def build_chart(daily):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["Equity"],
            mode="lines",
            name="Dual Momentum",
            line=dict(color="#60a5fa", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["SPY_Equity"],
            mode="lines",
            name="SPY",
            line=dict(color="#94a3b8", width=1.7),
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
        div_id="dual-momentum-equity-chart",
    )


def build_monthly_table(monthly, partial=None):
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    headers = "".join(f"<th>{name}</th>" for name in month_names + ["Year Return"])
    display = monthly.copy()
    partial_year = partial_month = None
    if partial is not None:
        partial_date = pd.Timestamp(partial["latest_day"])
        partial_year = partial_date.year
        partial_month = partial_date.strftime("%b")
        if partial_year not in display["Year"].astype(int).values:
            display = pd.concat([display, pd.DataFrame([{"Year": partial_year}])], ignore_index=True)
        display.loc[display["Year"].astype(int) == partial_year, partial_month] = float(partial["partial_return"])
        completed = display.loc[display["Year"].astype(int) == partial_year, month_names].iloc[0].dropna()
        display.loc[display["Year"].astype(int) == partial_year, "Year Return"] = (1.0 + completed).prod() - 1.0

    rows = []
    for item in display.sort_values("Year", ascending=False).itertuples(index=False):
        cells = []
        values = [getattr(item, name) for name in month_names]
        values.append(getattr(item, "_13"))
        for index, value in enumerate(values):
            if pd.isna(value):
                cells.append('<td class="muted">—</td>')
            else:
                css = "positive" if value > 0 else "negative" if value < 0 else "muted"
                is_partial = int(item.Year) == partial_year and index < 12 and month_names[index] == partial_month
                suffix = "*" if is_partial else ""
                title = ' title="Partial month-to-date return"' if is_partial else ""
                cells.append(f'<td class="{css}"{title}>{value * 100:.1f}%{suffix}</td>')
        rows.append(f"<tr><th>{int(item.Year)}</th>{''.join(cells)}</tr>")
    note = ""
    if partial is not None:
        note = f'<p class="subtle">* Partial month-to-date return through {html.escape(str(partial["latest_day"]))}.</p>'
    return note + (
        '<div class="table-wrap"><table><thead><tr><th>Year</th>'
        f'{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_page(summary, daily, allocations, monthly, alert, partial=None):
    chart_html = build_chart(daily)
    start_date = daily["Date"].min().strftime("%Y-%m-%d")
    end_date = daily["Date"].max().strftime("%Y-%m-%d")
    active_months = len(allocations)
    metrics = (
        ("Strategy CAGR", pct(summary.cagr)),
        ("Strategy Max Drawdown", pct(summary.daily_max_drawdown)),
        ("Total Return", pct(summary.total_return)),
        ("Sharpe Ratio", f"{summary.sharpe:.2f}"),
        ("SPY CAGR", pct(summary.spy_cagr)),
        ("SPY Max Drawdown", pct(summary.spy_daily_max_drawdown)),
        ("Final Equity", f"${summary.final:,.0f}"),
        ("Active Months", f"{active_months:,}"),
    )
    metric_html = "".join(
        f'<div class="metric"><div class="metric-label">{label}</div>'
        f'<div class="metric-value {metric_class(value)}">{value}</div></div>'
        for label, value in metrics
    )
    member_sections = (
        '<section class="panel"><h2>Member Signals</h2>'
        '<p class="subtle">Current holdings, latest alerts, and recent allocations are available to members.</p>'
        '<p><a href="subscribe.html">View membership options</a></p>'
        + build_position_calculator(
            [item.strip() for item in alert.get("Holdings", "").split(",")],
            "momoetf1-position-calculator",
        )
        + '</section>'
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Momentum ETFs Backtest - Extreme Trading Inc.</title>
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
<section class="hero"><div class="eyebrow">Backtested ETF allocation model</div><h1>MoMoEtf1</h1><p>Systematic ETF allocation model that adjusts monthly across major market exposures using proprietary trend and risk-management signals. Subscribers receive current model allocations and update alerts.</p><p class="subtle">Backtest period: {start_date} through {end_date} · Starting equity: ${daily.iloc[0]["Equity"]:,.0f}</p>{render_faq()}</section>
<section class="metrics">{metric_html}</section>
<section class="panel"><h2>Equity Curve</h2><p class="subtle">Dual Momentum compared with an equal-starting-equity SPY benchmark.</p><div class="chart">{chart_html}</div></section>
<section class="panel"><h2>Monthly Returns</h2>{build_monthly_table(monthly, partial)}</section>
{member_sections}
<section class="panel disclaimer"><strong>Important:</strong> These are simulated backtest results, not verified live performance. Backtests are hypothetical, may benefit from hindsight, and may not reflect transaction costs, slippage, liquidity constraints, taxes, or future market conditions. Past or simulated performance does not guarantee future results.</section>
</main>
<footer>© 2026 Extreme Trading Inc.</footer>
</body>
</html>"""


def main():
    args = parse_args()
    summary, daily, allocations, monthly, alert, partial = load_results(args.source)
    args.output.write_text(
        render_page(summary, daily, allocations, monthly, alert, partial),
        encoding="utf-8",
    )
    print(f"Generated {args.output} from {args.source}")


if __name__ == "__main__":
    main()
