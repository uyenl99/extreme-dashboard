import argparse
import html
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from strategy_faq import FAQ_CSS, render_faq
from metric_style import metric_class

from generate_momentum_page import (
    build_alert_table,
    build_monthly_table,
    pct,
)


REQUIRED_FILES = (
    "summary.csv",
    "daily_equity.csv",
    "monthly_results.csv",
    "monthly_return_table.csv",
)
INITIAL_EQUITY = 100_000.0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate the public MoMo Stocks backtest page."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("../MomoSp/pit_version/output_pit_v2a"),
        help="Directory containing the MOMO-SP v2a output files.",
    )
    parser.add_argument(
        "--alert-source",
        type=Path,
        default=Path("../MomoSp/pit_version/output_pit_v2a_live/latest_signal.json"),
        help="MOMO-SP v2a live-signal JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("momentum-stocks.html"),
        help="HTML file to generate.",
    )
    parser.add_argument(
        "--audience",
        choices=("public", "member"),
        default="public",
        help="Public omits current alerts and recent allocations.",
    )
    return parser.parse_args()


def load_alert(path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing MOMO-SP v2a alert file: {path}")
    signal = json.loads(path.read_text(encoding="utf-8"))
    holdings = signal.get("holdings") or [signal.get("defensive_holding")]
    alert = {
        "Signal": signal.get("signal_date", "—"),
        "Regime": signal.get("regime", "—"),
        "Holdings": ", ".join(item for item in holdings if item),
        "Execution": f'{signal.get("execution_date", "—")} open',
    }
    if signal.get("preliminary"):
        alert["Status"] = f'Preliminary through {signal.get("latest_price_date", "—")}'
    current = signal.get("current_allocation") or {}
    current_holdings = current.get("holdings") or holdings
    return alert, {
        "Signal": current.get("signal_date") or signal.get("signal_date", "—"),
        "Regime": current.get("regime") or signal.get("regime", "—"),
        "Holdings": ", ".join(item for item in current_holdings if item),
        "Execution": current.get("execution_date") or signal.get("execution_date", "—"),
        "Latest Price Date": current.get("latest_price_date") or signal.get("latest_price_date", "—"),
        "Partial Return": current.get("partial_return"),
        "SPY Partial Return": current.get("spy_partial_return"),
    }


def load_results(source, alert_source):
    missing = [name for name in REQUIRED_FILES if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing required MOMO-SP output files: {', '.join(missing)}"
        )

    summary = pd.read_csv(source / "summary.csv")
    if len(summary) != 1:
        raise ValueError("summary.csv must contain exactly one result row")

    daily = pd.read_csv(source / "daily_equity.csv", parse_dates=["date"])
    allocations = pd.read_csv(
        source / "monthly_results.csv",
        parse_dates=["entry_date", "signal_date", "exit_date"],
    )
    monthly = pd.read_csv(source / "monthly_return_table.csv")
    alert, current = load_alert(alert_source)

    for frame, column, label in (
        (daily, "date", "daily_equity"),
        (allocations, "entry_date", "monthly_results"),
    ):
        if frame[column].isna().any() or not frame[column].is_monotonic_increasing:
            raise ValueError(f"{label}.csv dates must be valid and sorted")

    return summary.iloc[0], daily, allocations, monthly, alert, current


def build_chart(daily):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["equity"],
            mode="lines",
            name="MoMo Stocks",
            line=dict(color="#60a5fa", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["spy_equity"],
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
        div_id="momentum-stocks-equity-chart",
    )


def build_allocation_table(allocations, current=None, limit=20):
    rows = []
    completed_limit = limit
    if current and current.get("Execution") not in (None, "", "—"):
        entry = pd.Timestamp(current["Execution"])
        risk_off = str(current.get("Regime", "")).strip().upper() == "RISK OFF"
        regime = "Risk Off" if risk_off else "Risk On"
        regime_css = "risk-off" if risk_off else "risk-on"
        partial_return = current.get("Partial Return")
        spy_partial_return = current.get("SPY Partial Return")
        return_text = "—" if partial_return is None else f"{float(partial_return) * 100:.2f}%"
        return_css = (
            "muted" if partial_return is None
            else "positive" if float(partial_return) > 0
            else "negative" if float(partial_return) < 0
            else "muted"
        )
        spy_text = "—" if spy_partial_return is None else f"{float(spy_partial_return) * 100:.2f}%"
        rows.append(
            '<tr>'
            f'<td title="Partial month-to-date through {html.escape(str(current.get("Latest Price Date", "—")))}">{entry:%Y-%m}*</td>'
            f'<td>{html.escape(str(current.get("Holdings", "—")))}</td>'
            f'<td><span class="regime {regime_css}">{regime}</span></td>'
            f'<td class="{return_css}">{return_text}</td>'
            f'<td>{spy_text}</td></tr>'
        )
        completed_limit -= 1
    recent = (
        allocations.rename(columns={"return": "strategy_return"})
        .sort_values("entry_date", ascending=False)
        .head(completed_limit)
    )
    for item in recent.itertuples(index=False):
        ret_css = "positive" if item.strategy_return > 0 else "negative"
        regime = "Risk Off" if item.risk_off else "Risk On"
        regime_css = "risk-off" if item.risk_off else "risk-on"
        rows.append(
            f"<tr><td>{item.entry_date:%Y-%m-%d}</td>"
            f"<td>{html.escape(str(item.holdings))}</td>"
            f'<td><span class="regime {regime_css}">{regime}</span></td>'
            f'<td class="{ret_css}">{item.strategy_return * 100:.2f}%</td>'
            f"<td>{item.spy_return * 100:.2f}%</td></tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr><th>Entry</th>'
        "<th>Holdings</th><th>Regime</th><th>Return</th><th>SPY</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def current_partial_month_panel(current):
    partial_return = current.get("Partial Return")
    if partial_return is None:
        return_text, return_class = "—", "muted"
    else:
        partial_return = float(partial_return)
        return_text = pct(partial_return)
        return_class = "positive" if partial_return > 0 else "negative" if partial_return < 0 else "muted"
    regime = str(current.get("Regime", "—")).replace("_", " ").title()
    return (
        '<section class="panel" id="current-month"><h2>Current Partial Month</h2>'
        f'<p class="subtle">Mark-to-market through {html.escape(str(current.get("Latest Price Date", "—")))}; this is an incomplete-month estimate.</p>'
        '<div class="metrics">'
        f'<div class="metric"><div class="metric-label">Current Month Return</div><div class="metric-value {return_class}">{return_text}</div></div>'
        f'<div class="metric"><div class="metric-label">Holdings</div><div class="metric-value positive">{html.escape(str(current.get("Holdings", "—")))}</div></div>'
        f'<div class="metric"><div class="metric-label">Regime</div><div class="metric-value">{html.escape(regime)}</div></div>'
        f'<div class="metric"><div class="metric-label">Entry Day</div><div class="metric-value">{html.escape(str(current.get("Execution", "—")))}</div></div>'
        '</div></section>'
    )


def render_page(summary, daily, allocations, monthly, alert, current, audience="public"):
    total_return = summary.final_equity / INITIAL_EQUITY - 1
    sharpe = summary.sharpe_0rf
    max_drawdown = summary.daily_max_drawdown
    metrics = (
        ("Strategy CAGR", pct(summary.cagr)),
        ("Strategy Max Drawdown", pct(max_drawdown)),
        ("Total Return", pct(total_return)),
        ("Sharpe Ratio", f"{sharpe:.2f}"),
        ("SPY CAGR", pct(summary.spy_cagr)),
        ("SPY Max Drawdown", pct(summary.spy_max_drawdown_period)),
        ("Final Equity", f"${summary.final_equity:,.0f}"),
        ("Active Months", f"{len(allocations):,}"),
    )
    metric_html = "".join(
        f'<div class="metric"><div class="metric-label">{label}</div>'
        f'<div class="metric-value {metric_class(value)}">{value}</div></div>'
        for label, value in metrics
    )
    chart_html = build_chart(daily)
    if audience == "member":
        protected_sections = (
            current_partial_month_panel(current)
            + '<section class="panel"><h2>Latest Alert</h2>'
            f'<p class="subtle">{html.escape(alert.get("Status", "Preliminary"))}. '
            'The current-month signal may change before execution.</p>'
            f'{build_alert_table(alert, ("Signal", "Regime", "Holdings", "Execution"))}</section>'
            f'<section class="panel"><h2>Latest 20 Historical Trades</h2>{build_allocation_table(allocations, current)}</section>'
        )
    else:
        protected_sections = (
            '<section class="panel"><h2>Member Signals</h2>'
            '<p class="subtle">Current holdings, latest alerts, and recent allocations are available to members.</p>'
            '<p><a href="subscribe.html">View membership options</a></p></section>'
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MoMo Stocks Backtest - Extreme Trading Inc.</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial,Helvetica,sans-serif}} nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 30px;background:#111827}} nav a{{color:white;text-decoration:none;margin-left:20px}} .container{{width:95%;max-width:1400px;margin:auto;padding:30px 20px 60px}} .hero,.panel{{background:#111827;border:1px solid #374151;border-radius:12px;padding:26px;margin-bottom:22px}} .eyebrow{{color:#60a5fa;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:bold}} h1{{margin:8px 0 10px}} h2{{margin-top:0}} .subtle,.muted{{color:#94a3b8}} .metrics{{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:14px;margin:22px 0}} .metric{{background:#111827;border:1px solid #374151;border-radius:10px;padding:18px}} .metric-label{{color:#94a3b8;font-size:13px}} .metric-value{{font-size:24px;font-weight:700;margin-top:6px}} .chart{{overflow:hidden}} .table-wrap{{overflow-x:auto}} table{{width:100%;border-collapse:collapse;background:#111827}} th,td{{border:1px solid #374151;padding:7px 9px;text-align:right;font-size:15px;white-space:nowrap}} th{{background:#1f2937;color:white}} th:first-child,td:first-child{{text-align:left}} .positive{{color:#22c55e;font-weight:600}} .negative{{color:#f87171;font-weight:600}} .compact{{max-width:420px}} .regime{{font-weight:700}} .risk-on{{color:#60a5fa}} .risk-off{{color:#f59e0b}} .disclaimer{{font-size:13px;line-height:1.6;color:#94a3b8}} footer{{text-align:center;padding:30px;color:#94a3b8}} @media(max-width:800px){{nav{{align-items:flex-start;padding:16px;gap:12px}}nav div:last-child{{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}}nav a{{margin-left:8px;font-size:12px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.container{{padding:20px 10px}}}} @media(max-width:480px){{.metrics{{grid-template-columns:1fr}}}}
{FAQ_CSS}</style>
</head>
<body>
<nav class="site-nav">
<strong class="brand">Extreme Trading Inc.</strong>
<div class="navlinks"><a href="index.html">Home</a><a href="strategies.html">Strategies</a><a href="subscribe.html">Subscribe</a><a href="members.html">Login</a><a href="about.html">About</a><a href="contact.html">Contact</a></div>
</nav>
<main class="container">
<section class="hero"><div class="eyebrow">Backtested stock allocation model</div><h1>MoMo Stocks</h1><p>Systematic stock allocation model that adjusts monthly across selected equity opportunities using proprietary trend, quality, and risk-management signals. Subscribers receive current model allocations and update alerts.</p><p class="subtle">Backtest period: {summary.start} through {summary.end} · Starting equity: ${INITIAL_EQUITY:,.0f}</p>{render_faq("momentum-stocks", audience)}</section>
<section class="metrics">{metric_html}</section>
{protected_sections if audience == "member" else ""}
<section class="panel"><h2>Equity Curve</h2><p class="subtle">MoMo Stocks compared with an equal-starting-equity SPY benchmark.</p><div class="chart">{chart_html}</div></section>
<section class="panel"><h2>Monthly Returns</h2>{build_monthly_table(monthly, daily=daily.rename(columns={"date": "Date", "spy_equity": "SPY_Equity"}))}</section>
{protected_sections if audience == "public" else ""}
<section class="panel disclaimer"><strong>Important:</strong> These are simulated backtest results, not verified live performance. Backtests are hypothetical, may benefit from hindsight, and may not reflect transaction costs, slippage, liquidity constraints, taxes, or future market conditions. Past or simulated performance does not guarantee future results.</section>
</main>
<footer>© 2026 Extreme Trading Inc.</footer>
</body>
</html>"""


def main():
    args = parse_args()
    summary, daily, allocations, monthly, alert, current = load_results(
        args.source, args.alert_source
    )
    page = render_page(summary, daily, allocations, monthly, alert, current, args.audience)
    if args.audience == "public":
        forbidden = ("<h2>Current Partial Month</h2>", "<h2>Latest Alert</h2>", "<h2>Latest 20 Historical Trades</h2>")
        leaked = [item for item in forbidden if item in page]
        if leaked:
            raise RuntimeError(f"Public Momentum Stocks page contains member-only content: {leaked}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")
    print(f"Generated {args.audience} {args.output} from {args.source}")


if __name__ == "__main__":
    main()
