import argparse
import html
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from strategy_faq import FAQ_CSS, render_faq
from metric_style import metric_class
from strategy_benchmark import yearly_returns_by_year


REQUIRED_FILES = (
    "summary_stats.csv",
    "equity_curve.csv",
    "benchmark_curve.csv",
    "monthly_returns.csv",
    "trades.csv",
    "daily_trades.csv",
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate the public Mean Reversion backtest page."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("../RevMurphy/output_long_short_live"),
        help="Directory containing the live RevMurphy output CSV files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("mean-reversion.html"),
        help="HTML file to generate.",
    )
    parser.add_argument(
        "--alert-source",
        type=Path,
        default=Path("../RevMurphy/output_live_alerts"),
        help="Directory containing dated Mean Reversion live-alert CSV files.",
    )
    parser.add_argument(
        "--strategies-page",
        type=Path,
        default=Path("index.html"),
        help="Strategies page whose Mean Reversion card metrics should be refreshed.",
    )
    parser.add_argument(
        "--audience",
        choices=("public", "member"),
        default="public",
        help="Public omits alerts, positions, portfolio actions, and recent trades.",
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
    trades = pd.read_csv(source / "trades.csv")
    daily_trades = pd.read_csv(source / "daily_trades.csv", parse_dates=["date"])

    for frame, label in ((equity, "equity_curve"), (benchmarks, "benchmark_curve")):
        if frame["date"].isna().any() or not frame["date"].is_monotonic_increasing:
            raise ValueError(f"{label}.csv dates must be valid and sorted")

    if daily_trades.empty or daily_trades["date"].isna().any():
        raise ValueError("daily_trades.csv must contain valid alert dates")

    return summary.iloc[0], equity, benchmarks, monthly, trades, daily_trades


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


def build_monthly_table(monthly, benchmarks):
    data = monthly.copy()
    data["year"] = data["month"].astype(str).str[:4].astype(int)
    data["month_number"] = data["month"].astype(str).str[5:7].astype(int)
    pivot = data.pivot(index="year", columns="month_number", values="return_pct")
    pivot["YTD"] = pivot.apply(
        lambda row: ((1 + row.dropna()).prod() - 1), axis=1
    )
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    spy_year = yearly_returns_by_year(benchmarks["date"], benchmarks["SPY_equity"])
    pivot["SPY Year"] = pd.Series(pivot.index, index=pivot.index).map(spy_year)
    columns = list(range(1, 13)) + ["YTD", "SPY Year"]
    head = "".join(f"<th>{label}</th>" for label in labels + ["YTD", "SPY Year"])
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


def load_live_alert(daily_trades, alert_source):
    entry_files = sorted(alert_source.glob("entry_alerts_*.csv"))
    if not entry_files:
        raise FileNotFoundError(f"No Mean Reversion entry alerts found in {alert_source}")
    entry_path = entry_files[-1]
    exit_path = alert_source / entry_path.name.replace("entry_alerts_", "exit_alerts_")
    if not exit_path.is_file():
        raise FileNotFoundError(f"Missing matching Mean Reversion exit alerts: {exit_path}")

    entries = pd.read_csv(entry_path)
    exits = pd.read_csv(exit_path)
    signal_date = pd.to_datetime(entries["date"].iloc[0])
    if "side" in entries.columns:
        sides = entries["side"].fillna("").astype(str).str.lower()
        long_entries = entries.loc[sides == "long", "ticker"].dropna().astype(str).tolist()
        short_entries = entries.loc[sides == "short", "ticker"].dropna().astype(str).tolist()
    else:
        long_entries = entries["ticker"].dropna().astype(str).tolist()
        short_entries = []
    entry_sides = {ticker: "Long" for ticker in long_entries}
    entry_sides.update({ticker: "Short" for ticker in short_entries})

    date_tag = entry_path.stem.replace("entry_alerts_", "")
    holdings_path = alert_source / f"portfolio_holdings_{date_tag}.csv"
    portfolio_exits_path = alert_source / f"portfolio_exit_alerts_{date_tag}.csv"
    if holdings_path.is_file():
        holdings = pd.read_csv(holdings_path)
        held_positions = [
            (str(row.ticker), str(row.side).title())
            for row in holdings.dropna(subset=["ticker"]).itertuples(index=False)
        ]
    else:
        latest = daily_trades.sort_values("date").iloc[-1]
        held_with_sides = str(latest.get("current_tickers_held", "")).split(",")
        held_positions = []
        for item in held_with_sides:
            if not item:
                continue
            parts = item.split(":", 1)
            held_positions.append(
                (parts[-1], parts[0].title() if len(parts) == 2 else "Unknown")
            )
    portfolio_exits = pd.read_csv(portfolio_exits_path) if portfolio_exits_path.is_file() else exits
    exit_sides = {
        str(row.ticker): str(getattr(row, "side", "Unknown")).title()
        for row in portfolio_exits.dropna(subset=["ticker"]).itertuples(index=False)
    }
    exit_positions = [
        (ticker, exit_sides.get(ticker, side))
        for ticker, side in held_positions
        if ticker in exit_sides
    ]
    projected = [
        (ticker, side) for ticker, side in held_positions if ticker not in exit_sides
    ]
    trade_entries_path = alert_source / f"trade_entries_{date_tag}.csv"
    if trade_entries_path.is_file():
        trade_entries = pd.read_csv(trade_entries_path)
        projected_entries = [
            (str(row.ticker), str(row.side).title())
            for row in trade_entries.dropna(subset=["ticker"]).itertuples(index=False)
        ]
    else:
        projected_entries = [(ticker, side) for ticker, side in entry_sides.items()]
    projected_tickers = {ticker for ticker, _ in projected}
    projected.extend(
        (ticker, side)
        for ticker, side in projected_entries
        if ticker not in projected_tickers
    )
    return signal_date, long_entries, short_entries, exit_positions, projected


def format_positions(positions):
    return ", ".join(f"{ticker} ({side})" for ticker, side in positions)


def read_optional_csv(path):
    if not path.is_file() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def build_moo_order_tables(trades, total_equity, results_through):
    data = trades.copy()
    data["entry_date"] = pd.to_datetime(data["entry_date"], errors="coerce")
    data["exit_date"] = pd.to_datetime(data["exit_date"], errors="coerce")
    closed = data["status"].fillna("").astype(str).str.lower().eq("closed")
    latest_dates = [data["entry_date"].max(), data.loc[closed, "exit_date"].max()]
    latest_dates = [date for date in latest_dates if pd.notna(date)]
    execution_date = max(latest_dates) if latest_dates else pd.Timestamp.today().normalize()
    entries = data[data["entry_date"].eq(execution_date)]
    exits = data[closed & data["exit_date"].eq(execution_date)]

    order_rows = []
    for row in exits.itertuples(index=False):
        side = str(row.side).title()
        order_rows.append(
            f"<tr><td>Exit</td><td>{html.escape(str(row.ticker))}</td>"
            f'<td><span class="side {side.lower()}">{side}</span></td>'
            f"<td>${float(row.entry_notional):,.0f}</td><td>{float(row.shares):,.2f}</td>"
            f"<td>${float(row.exit_price):,.2f}</td></tr>"
        )
    for row in entries.itertuples(index=False):
        side = str(row.side).title()
        action = "Buy" if side.lower() == "long" else "Sell Short"
        order_rows.append(
            f"<tr><td>{action}</td><td>{html.escape(str(row.ticker))}</td>"
            f'<td><span class="side {side.lower()}">{side}</span></td>'
            f"<td>${float(row.entry_notional):,.0f}</td><td>{float(row.shares):,.2f}</td>"
            f"<td>${float(row.entry_price):,.2f}</td></tr>"
        )
    if not order_rows:
        order_rows.append('<tr><td colspan="6" class="muted">None - no MOO orders on the latest execution date.</td></tr>')
    orders = (
        f'<p class="subtle">Results through: {results_through:%Y-%m-%d} · Latest order execution date: {execution_date:%Y-%m-%d}. Signals use completed daily bars and orders fill at the next market open.</p>'
        '<div class="table-wrap"><table><thead><tr><th>Action</th><th>Ticker</th>'
        '<th>Direction</th><th>Position Value</th><th>Shares</th>'
        f'<th>MOO Fill Price</th></tr></thead><tbody>{"".join(order_rows)}</tbody></table></div>'
    )

    position_rows = []
    holdings = data[~closed].sort_values(["side", "entry_date", "ticker"])
    for row in holdings.itertuples(index=False):
        side = str(row.side).title()
        position_value = abs(float(row.entry_notional))
        weight = position_value / total_equity if total_equity else 0.0
        position_rows.append(
            f"<tr><td>{html.escape(str(row.ticker))}</td>"
            f'<td><span class="side {side.lower()}">{side}</span></td>'
            f"<td>{row.entry_date:%Y-%m-%d}</td><td>{float(row.shares):,.2f}</td>"
            f"<td>${float(row.entry_price):,.2f}</td><td>${position_value:,.0f}</td>"
            f"<td>{weight * 100:.2f}%</td></tr>"
        )
    if not position_rows:
        position_rows.append('<tr><td colspan="7" class="muted">No open positions.</td></tr>')
    positions = (
        f'<p class="subtle">Total strategy equity: ${total_equity:,.0f}</p>'
        '<div class="table-wrap"><table><thead><tr><th>Ticker</th><th>Direction</th>'
        '<th>Entry Date</th><th>Shares</th><th>Entry Price</th><th>Entry Position Value</th>'
        f'<th>Position Size (% Equity)</th></tr></thead><tbody>{"".join(position_rows)}</tbody></table></div>'
    )
    return orders, positions


def build_portfolio_tables(alert_source, signal_date, total_equity):
    date_tag = signal_date.strftime("%Y%m%d")
    entries = read_optional_csv(alert_source / f"trade_entries_{date_tag}.csv")
    exits = read_optional_csv(alert_source / f"portfolio_exit_alerts_{date_tag}.csv")
    holdings = read_optional_csv(alert_source / f"portfolio_holdings_{date_tag}.csv")

    change_rows = []
    for row in exits.itertuples(index=False):
        side = str(row.side).title()
        change_rows.append(
            f"<tr><td>Exit</td><td>{html.escape(str(row.ticker))}</td>"
            f'<td><span class="side {side.lower()}">{side}</span></td>'
            f"<td>Close position</td><td>—</td><td>${float(row.close):,.2f}</td></tr>"
        )
    for row in entries.itertuples(index=False):
        side = str(row.side).title()
        target_value = total_equity * 0.80 / 5 if side.lower() == "long" else total_equity * 0.20 / 5
        price = float(row.close)
        estimated_shares = target_value / price if price else 0.0
        action = "Buy" if side.lower() == "long" else "Sell Short"
        change_rows.append(
            f"<tr><td>{action}</td><td>{html.escape(str(row.ticker))}</td>"
            f'<td><span class="side {side.lower()}">{side}</span></td>'
            f"<td>${target_value:,.0f}</td><td>{estimated_shares:,.2f}</td>"
            f"<td>${price:,.2f}</td></tr>"
        )
    if not change_rows:
        change_rows.append('<tr><td colspan="6" class="muted">None — no portfolio changes today.</td></tr>')
    changes = (
        '<div class="table-wrap"><table><thead><tr><th>Action</th><th>Ticker</th>'
        '<th>Direction</th><th>Target Position Value</th><th>Estimated Shares</th>'
        f'<th>Alert Price</th></tr></thead><tbody>{"".join(change_rows)}</tbody></table></div>'
    )

    position_rows = []
    for row in holdings.itertuples(index=False):
        side = str(row.side).title()
        shares = float(row.shares)
        price = float(row.close)
        position_value = abs(shares * price)
        weight = position_value / total_equity if total_equity else 0.0
        position_rows.append(
            f"<tr><td>{html.escape(str(row.ticker))}</td>"
            f'<td><span class="side {side.lower()}">{side}</span></td>'
            f"<td>{shares:,.2f}</td><td>${price:,.2f}</td>"
            f"<td>${position_value:,.0f}</td><td>{weight * 100:.2f}%</td></tr>"
        )
    if not position_rows:
        position_rows.append('<tr><td colspan="6" class="muted">No open positions.</td></tr>')
    positions = (
        f'<p class="subtle">Total strategy equity: ${total_equity:,.0f}</p>'
        '<div class="table-wrap"><table><thead><tr><th>Ticker</th><th>Direction</th>'
        '<th>Shares</th><th>Current Price</th><th>Current Position Value</th>'
        f'<th>Position Size (% Equity)</th></tr></thead><tbody>{"".join(position_rows)}</tbody></table></div>'
    )
    return changes, positions


def build_alert_table(daily_trades, alert_source, total_equity):
    signal_date, long_entries, short_entries, exit_positions, projected = load_live_alert(
        daily_trades, alert_source
    )
    longs = html.escape(format_positions((ticker, "Long") for ticker in long_entries) or "—")
    shorts = html.escape(format_positions((ticker, "Short") for ticker in short_entries) or "—")
    exits = html.escape(format_positions(exit_positions) or "—")
    holdings = html.escape(format_positions(projected) or "—")
    alerts = (
        '<div class="table-wrap"><table><thead><tr><th>Signal Date</th>'
        '<th>Long Entry Alerts</th><th>Short Entry Alerts</th><th>Exit Alerts</th>'
        '<th>Projected Holdings</th></tr></thead>'
        f'<tbody><tr><td>{signal_date:%Y-%m-%d}</td><td>{longs}</td><td>{shorts}</td>'
        f'<td>{exits}</td><td>{holdings}</td></tr></tbody></table></div>'
    )
    changes, positions = build_portfolio_tables(alert_source, signal_date, total_equity)
    return alerts, changes, positions


def build_trade_table(trades, limit=20):
    recent = trades.copy()
    recent["entry_date"] = pd.to_datetime(recent["entry_date"], errors="coerce")
    recent["exit_date"] = pd.to_datetime(recent["exit_date"], errors="coerce")
    recent["is_closed"] = recent["status"].fillna("").astype(str).str.lower().eq("closed")
    recent["sort_date"] = recent["exit_date"].where(recent["is_closed"], recent["entry_date"])
    recent = recent.sort_values(
        ["is_closed", "sort_date", "entry_date"],
        ascending=[True, False, False],
        kind="stable",
    ).head(limit)
    rows = []
    for item in recent.itertuples(index=False):
        is_closed = str(item.status).lower() == "closed"
        css = "positive" if is_closed and item.pnl_dollars >= 0 else "negative" if is_closed else "muted"
        side_css = "long" if str(item.side).lower() == "long" else "short"
        exit_date = item.exit_date.strftime("%Y-%m-%d") if is_closed else "—"
        exit_price = f"${float(item.exit_price):,.2f}" if is_closed else "—"
        pnl = f"${float(item.pnl_dollars):,.0f}" if is_closed else "—"
        trade_return = f"{float(item.return_pct) * 100:.2f}%" if is_closed else "—"
        rows.append(
            f"<tr><td>{html.escape(str(item.ticker))}</td>"
            f'<td><span class="side {side_css}">{html.escape(str(item.side).title())}</span></td>'
            f"<td>{item.entry_date:%Y-%m-%d}</td><td>${float(item.entry_price):,.2f}</td>"
            f"<td>{exit_date}</td><td>{exit_price}</td>"
            f'<td class="{css}">{pnl}</td><td class="{css}">{trade_return}</td>'
            f"<td>{html.escape(str(item.status).title())}</td></tr>"
        )
    return f'<div class="table-wrap"><table><thead><tr><th>Ticker</th><th>Side</th><th>Entry Date</th><th>Entry Price</th><th>Exit Date</th><th>Exit Price</th><th>P/L</th><th>Return</th><th>Status</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def update_strategy_card(path, summary):
    text = path.read_text(encoding="utf-8")
    start = text.index("<h2>Mean Reversion</h2>")
    end = text.index("</div>", start)
    card = text[start:end]
    card = re.sub(r"[\d.]+% Backtest CAGR", f"{summary.cagr * 100:.2f}% Backtest CAGR", card)
    card = re.sub(r"[\d.]+ Sharpe Ratio", f"{summary.annualized_sharpe:.2f} Sharpe Ratio", card)
    card = re.sub(r"-[\d.]+% Maximum Drawdown", f"{summary.max_drawdown * 100:.2f}% Maximum Drawdown", card)
    path.write_text(text[:start] + card + text[end:], encoding="utf-8")


def render_page(summary, equity, benchmarks, monthly, trades, daily_trades, alert_source, audience="public"):
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
    if audience == "member":
        moo_orders, latest_positions = build_moo_order_tables(
            trades, float(equity.iloc[-1]["equity"]), equity.iloc[-1]["date"]
        )
        protected_sections = (
            f'<section class="panel"><h2>Latest MOO Orders</h2>{moo_orders}</section>'
            f'<section class="panel"><h2>Open Positions</h2>{latest_positions}</section>'
            f'<section class="panel"><h2>Latest 20 Trades</h2>{build_trade_table(trades)}</section>'
        )
    else:
        protected_sections = (
            '<section class="panel"><h2>Member Signals</h2>'
            '<p class="subtle">Latest MOO orders, current positions, and recent trades are available to members.</p>'
            '<p><a href="subscribe.html">View membership options</a></p></section>'
        )
    chart_html = build_chart(equity, benchmarks)
    spy = benchmarks[["date", "SPY_equity"]].dropna()
    spy_years = (spy["date"].iloc[-1] - spy["date"].iloc[0]).days / 365.25
    spy_cagr = (spy["SPY_equity"].iloc[-1] / spy["SPY_equity"].iloc[0]) ** (1 / spy_years) - 1
    spy_drawdown = (spy["SPY_equity"] / spy["SPY_equity"].cummax() - 1).min()
    metrics = (
        ("Strategy CAGR", pct(summary.cagr)),
        ("Strategy Max Drawdown", pct(summary.max_drawdown)),
        ("Total Return", pct(summary.total_return)),
        ("Sharpe Ratio", f"{summary.annualized_sharpe:.2f}"),
        ("SPY CAGR", pct(spy_cagr)),
        ("SPY Max Drawdown", pct(spy_drawdown)),
        ("Final Equity", f"${summary.final_equity:,.0f}"),
        ("Closed Trades", f"{int(summary.trades):,}"),
        ("Win Rate", pct(summary.win_rate)),
        ("Average Trade", pct(summary.avg_trade_return)),
    )
    metric_html = "".join(
        f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value {metric_class(value)}">{value}</div></div>'
        for label, value in metrics
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mean Reversion Backtest - Extreme Trading Inc.</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial,Helvetica,sans-serif}} nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 30px;background:#111827}} nav a{{color:white;text-decoration:none;margin-left:20px}} .container{{width:95%;max-width:1400px;margin:auto;padding:30px 20px 60px}} .hero,.panel{{background:#111827;border:1px solid #374151;border-radius:12px;padding:26px;margin-bottom:22px}} .eyebrow{{color:#60a5fa;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:bold}} h1{{margin:8px 0 10px}} h2{{margin-top:0}} .subtle,.muted{{color:#94a3b8}} .metrics{{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:14px;margin:22px 0}} .metric{{background:#111827;border:1px solid #374151;border-radius:10px;padding:18px}} .metric-label{{color:#94a3b8;font-size:13px}} .metric-value{{font-size:24px;font-weight:700;margin-top:6px}} .chart{{overflow:hidden}} .table-wrap{{overflow-x:auto}} table{{width:100%;border-collapse:collapse;background:#111827}} th,td{{border:1px solid #374151;padding:7px 9px;text-align:right;font-size:15px;white-space:nowrap}} th{{background:#1f2937;color:white}} th:first-child,td:first-child{{text-align:left}} .positive{{color:#22c55e;font-weight:600}} .negative{{color:#f87171;font-weight:600}} .compact{{max-width:680px}} .side{{font-weight:700}} .side.long{{color:#60a5fa}} .side.short{{color:#f59e0b}} .disclaimer{{font-size:13px;line-height:1.6;color:#94a3b8}} footer{{text-align:center;padding:30px;color:#94a3b8}} @media(max-width:800px){{nav{{align-items:flex-start;padding:16px;gap:12px}}nav div:last-child{{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}}nav a{{margin-left:8px;font-size:12px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.container{{padding:20px 10px}}}} @media(max-width:480px){{.metrics{{grid-template-columns:1fr}}}}
{FAQ_CSS}</style>
</head>
<body>
<nav><div><strong>Extreme Trading Inc.</strong></div><div><a href="index.html">Home</a><a href="subscribe.html">Subscribe</a><a href="members.html">Login</a></div></nav>
<main class="container">
<section class="hero"><div class="eyebrow">Next-day MOO long/short strategy</div><h1>Mean Reversion</h1><p>Systematic equity strategy seeking short-term price dislocations and subsequent reversion while managing long and short exposure. Signals use completed daily bars and simulated entries and exits fill at the next market open.</p><p class="subtle">Backtest period: {summary.start_date} through {summary.end_date} · Starting equity: ${equity.iloc[0]['equity']:,.0f}</p><p class="subtle">Dashboard updated: {generated_at}</p>{render_faq("mean-reversion", audience)}</section>
<section class="metrics">{metric_html}</section>
{protected_sections if audience == "member" else ""}
<section class="panel"><h2>Equity Curve</h2><p class="subtle">Select SPY, QQQ, or VOO in the legend to add benchmark comparisons.</p><div class="chart">{chart_html}</div></section>
<section class="panel"><h2>Monthly Returns</h2>{build_monthly_table(monthly, benchmarks)}</section>
{protected_sections if audience == "public" else ""}
<section class="panel disclaimer"><strong>Important:</strong> These are simulated backtest results, not verified live performance. Backtests are hypothetical, may benefit from hindsight, and may not reflect transaction costs, slippage, liquidity constraints, taxes, or future market conditions. Past or simulated performance does not guarantee future results.</section>
</main>
<footer>© 2026 Extreme Trading Inc.</footer>
</body>
</html>"""


def main():
    args = parse_args()
    summary, equity, benchmarks, monthly, trades, daily_trades = load_results(args.source)
    page = render_page(
            summary, equity, benchmarks, monthly, trades, daily_trades,
            args.alert_source, args.audience,
    )
    if args.audience == "public":
        forbidden = (
            "<h2>Latest MOO Orders</h2>",
            "<h2>Open Positions</h2>",
            "<h2>Latest 20 Trades</h2>",
        )
        leaked = [item for item in forbidden if item in page]
        if leaked:
            raise RuntimeError(f"Public Mean Reversion page contains member-only content: {leaked}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")
    update_strategy_card(args.strategies_page, summary)
    print(f"Generated {args.audience} {args.output} from {args.source}")


if __name__ == "__main__":
    main()
