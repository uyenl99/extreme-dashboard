import argparse
import html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from strategy_faq import FAQ_CSS, render_faq
from metric_style import metric_class
from strategy_benchmark import yearly_returns_by_year


REQUIRED_FILES = (
    "summary.csv",
    "daily_equity_entries_exits.csv",
    "dual_momentum_results.csv",
    "monthly_return_table.csv",
    "next_entry_alert.txt",
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
    parser.add_argument(
        "--audience",
        choices=("public", "member"),
        default="public",
        help="Public omits current holdings, alerts, and recent allocations.",
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
        "risk filter": "Regime",
        "regime": "Regime",
        "holdings": "Holdings",
        "execute at": "Execution",
        "execution": "Execution",
        "vix 30d ma": "VIX 30d MA",
        "spy 10d realized vol": "SPY 10d RV",
        "spy 10d rv": "SPY 10d RV",
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


def build_alert_table(alert, columns=None):
    columns = columns or ("Signal", "Regime", "Holdings", "Execution", "VIX 30d MA", "SPY 10d RV")
    headers = "".join(f"<th>{column}</th>" for column in columns)
    cells = []
    for column in columns:
        value = html.escape(alert.get(column, "—"))
        css = ""
        if column == "Regime":
            css = ' class="regime risk-off"' if "OFF" in value.upper() else ' class="regime risk-on"'
        cells.append(f"<td{css}>{value}</td>")
    return f'<div class="table-wrap"><table><thead><tr>{headers}</tr></thead><tbody><tr>{"".join(cells)}</tr></tbody></table></div>'


def build_chart(daily):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["Equity"],
            mode="lines",
            name="MoMoEtf1",
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
        div_id="momoetf1-equity-chart",
    )


def build_monthly_table(monthly, partial=None, daily=None):
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    headers = "".join(f"<th>{name}</th>" for name in month_names + ["Year Return", "SPY Year"])
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

    spy_year = yearly_returns_by_year(daily["Date"], daily["SPY_Equity"]) if daily is not None else pd.Series(dtype="float64")
    rows = []
    for item in display.sort_values("Year", ascending=False).itertuples(index=False):
        cells = []
        values = [getattr(item, name) for name in month_names]
        values.extend((getattr(item, "_13"), spy_year.get(int(item.Year))))
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


def build_allocation_table(allocations, partial=None, limit=20):
    rows = []
    completed_limit = limit
    if partial is not None:
        risk_off = str(partial.get("risk_off", "")).strip().lower() in ("true", "1", "yes")
        regime = "Risk Off" if risk_off else "Risk On"
        regime_css = "risk-off" if risk_off else "risk-on"
        partial_return = float(partial["partial_return"])
        return_css = "positive" if partial_return > 0 else "negative" if partial_return < 0 else "muted"
        entry_month = pd.Timestamp(partial["entry_month"]).strftime("%Y-%m")
        rows.append(
            '<tr>'
            f'<td title="Partial month-to-date through {html.escape(str(partial["latest_day"]))}">{entry_month}*</td>'
            f"<td>{html.escape(str(partial['holdings']))}</td>"
            f'<td><span class="regime {regime_css}">{regime}</span></td>'
            f'<td class="{return_css}">{partial_return * 100:.2f}%</td>'
            '<td class="muted">—</td></tr>'
        )
        completed_limit -= 1
    recent = allocations.sort_values("date", ascending=False).head(completed_limit)
    for item in recent.itertuples(index=False):
        ret_css = "positive" if item.port_ret > 0 else "negative"
        regime = "Risk Off" if item.risk_off else "Risk On"
        regime_css = "risk-off" if item.risk_off else "risk-on"
        holdings = ", ".join(dict.fromkeys([item.h1, item.h2, item.h3]))
        rows.append(
            f"<tr><td>{item.date:%Y-%m}</td>"
            f"<td>{html.escape(holdings)}</td>"
            f'<td><span class="regime {regime_css}">{regime}</span></td>'
            f'<td class="{ret_css}">{item.port_ret * 100:.2f}%</td>'
            f"<td>{item.spy_ret * 100:.2f}%</td></tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr><th>Month</th>'
        "<th>Holdings</th><th>Regime</th><th>Return</th><th>SPY</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def current_partial_month_panel(partial):
    if partial is None:
        return ""
    risk_off = str(partial.get("risk_off", "")).strip().lower() in ("true", "1", "yes")
    regime = "Risk Off" if risk_off else "Risk On"
    return_value = float(partial["partial_return"])
    return_class = "positive" if return_value > 0 else "negative" if return_value < 0 else "muted"
    return (
        '<section class="panel" id="current-month"><h2>Current Partial Month</h2>'
        f'<p class="subtle">Mark-to-market through {html.escape(str(partial["latest_day"]))}; this is an incomplete-month estimate.</p>'
        '<div class="metrics">'
        f'<div class="metric"><div class="metric-label">Current Month Return</div><div class="metric-value {return_class}">{pct(return_value)}</div></div>'
        f'<div class="metric"><div class="metric-label">Holdings</div><div class="metric-value positive">{html.escape(str(partial["holdings"]))}</div></div>'
        f'<div class="metric"><div class="metric-label">Regime</div><div class="metric-value">{regime}</div></div>'
        f'<div class="metric"><div class="metric-label">Entry Day</div><div class="metric-value">{html.escape(str(partial["entry_day"]))}</div></div>'
        '</div></section>'
    )


def render_page(summary, daily, allocations, monthly, alert, partial=None, audience="public"):
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
    member_sections = ""
    if audience == "member":
        member_sections = (
            current_partial_month_panel(partial)
            + f'<section class="panel"><h2>Latest Alert</h2>{build_alert_table(alert, ("Signal", "Regime", "Holdings", "Execution"))}</section>'
            f'<section class="panel"><h2>Latest 20 Historical Trades</h2>{build_allocation_table(allocations, partial)}</section>'
        )
    else:
        member_sections = (
            '<section class="panel"><h2>Member Signals</h2>'
            '<p class="subtle">Current holdings, latest alerts, and recent allocations are available to members.</p>'
            '<p><a href="subscribe.html">View membership options</a></p></section>'
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MoMoEtf1 Backtest - Extreme Trading Inc.</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial,Helvetica,sans-serif}} nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 30px;background:#111827}} nav a{{color:white;text-decoration:none;margin-left:20px}} .container{{width:95%;max-width:1400px;margin:auto;padding:30px 20px 60px}} .hero,.panel{{background:#111827;border:1px solid #374151;border-radius:12px;padding:26px;margin-bottom:22px}} .eyebrow{{color:#60a5fa;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:bold}} h1{{margin:8px 0 10px}} h2{{margin-top:0}} .subtle,.muted{{color:#94a3b8}} .metrics{{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:14px;margin:22px 0}} .metric{{background:#111827;border:1px solid #374151;border-radius:10px;padding:18px}} .metric-label{{color:#94a3b8;font-size:13px}} .metric-value{{font-size:24px;font-weight:700;margin-top:6px}} .chart{{overflow:hidden}} .table-wrap{{overflow-x:auto}} table{{width:100%;border-collapse:collapse;background:#111827}} th,td{{border:1px solid #374151;padding:7px 9px;text-align:right;font-size:15px;white-space:nowrap}} th{{background:#1f2937;color:white}} th:first-child,td:first-child{{text-align:left}} .positive{{color:#22c55e;font-weight:600}} .negative{{color:#f87171;font-weight:600}} .compact{{max-width:420px}} .regime{{font-weight:700}} .risk-on{{color:#60a5fa}} .risk-off{{color:#f59e0b}} .disclaimer{{font-size:13px;line-height:1.6;color:#94a3b8}} footer{{text-align:center;padding:30px;color:#94a3b8}} @media(max-width:800px){{nav{{align-items:flex-start;padding:16px;gap:12px}}nav div:last-child{{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}}nav a{{margin-left:8px;font-size:12px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.container{{padding:20px 10px}}}} @media(max-width:480px){{.metrics{{grid-template-columns:1fr}}}}
{FAQ_CSS}</style>
</head>
<body>
<nav><div><strong>Extreme Trading Inc.</strong></div><div><a href="index.html">Home</a><a href="subscribe.html">Subscribe</a><a href="members.html">Login</a></div></nav>
<main class="container">
<section class="hero"><div class="eyebrow">Backtested ETF allocation model</div><h1>MoMoEtf1</h1><p>Systematic ETF allocation model that adjusts monthly across major market exposures using proprietary trend and risk-management signals. Subscribers receive current model allocations and update alerts.</p><p class="subtle">Backtest period: {start_date} through {end_date} · Starting equity: ${daily.iloc[0]["Equity"]:,.0f}</p>{render_faq("momentum", audience)}</section>
<section class="metrics">{metric_html}</section>
{member_sections if audience == "member" else ""}
<section class="panel"><h2>Equity Curve</h2><p class="subtle">MoMoEtf1 compared with an equal-starting-equity SPY benchmark.</p><div class="chart">{chart_html}</div></section>
<section class="panel"><h2>Monthly Returns</h2>{build_monthly_table(monthly, partial, daily)}</section>
{member_sections if audience == "public" else ""}
<section class="panel disclaimer"><strong>Important:</strong> These are simulated backtest results, not verified live performance. Backtests are hypothetical, may benefit from hindsight, and may not reflect transaction costs, slippage, liquidity constraints, taxes, or future market conditions. Past or simulated performance does not guarantee future results.</section>
</main>
<footer>© 2026 Extreme Trading Inc.</footer>
</body>
</html>"""


def validate_public_page(page):
    forbidden = (
        "<h2>Latest Alert</h2>",
        "<h2>Latest 20 Historical Trades</h2>",
        "<h2>Current Partial Month</h2>",
        'id="current-month"',
        "Entry</th><th>Latest</th><th>Return",
    )
    leaked = [value for value in forbidden if value in page]
    if leaked:
        raise RuntimeError(f"Public Momentum ETF page contains member-only content: {leaked}")


def main():
    args = parse_args()
    summary, daily, allocations, monthly, alert, partial = load_results(args.source)
    page = render_page(
        summary, daily, allocations, monthly, alert, partial, audience=args.audience
    )
    if args.audience == "public":
        validate_public_page(page)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")
    print(f"Generated {args.audience} {args.output} from {args.source}")


if __name__ == "__main__":
    main()
