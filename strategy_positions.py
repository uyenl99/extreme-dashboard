import html
from collections import Counter


def calculate_open_positions(
    holdings,
    entry_date,
    entry_prices,
    current_prices,
    portfolio_equity,
    weights=None,
):
    """Build model-position rows using fractional shares and entry-date equity."""
    ordered = list(dict.fromkeys(str(ticker) for ticker in holdings if ticker))
    if weights is None:
        counts = Counter(str(ticker) for ticker in holdings if ticker)
        total_slots = sum(counts.values())
        weights = {ticker: counts[ticker] / total_slots for ticker in ordered}

    rows = []
    for ticker in ordered:
        weight = float(weights[ticker])
        entry_price = float(entry_prices[ticker])
        current_price = float(current_prices[ticker])
        shares = float(portfolio_equity) * weight / entry_price
        position_value = shares * current_price
        open_pl = shares * (current_price - entry_price)
        rows.append(
            {
                "ticker": ticker,
                "entry_date": str(entry_date),
                "shares": shares,
                "entry_price": entry_price,
                "current_price": current_price,
                "position_value": position_value,
                "open_pl": open_pl,
                "open_pl_pct": current_price / entry_price - 1.0,
            }
        )
    return rows


def render_open_positions_table(rows):
    headers = (
        "Ticker",
        "Entry Date",
        "Shares",
        "Entry Price",
        "Current Price",
        "Position Value",
        "Open P/L",
        "Open P/L %",
    )
    body = []
    for row in rows:
        pnl = float(row["open_pl"])
        pnl_pct = float(row["open_pl_pct"])
        pnl_class = "positive" if pnl > 0 else "negative" if pnl < 0 else "muted"
        body.append(
            "<tr>"
            f'<td>{html.escape(str(row["ticker"]))}</td>'
            f'<td>{html.escape(str(row["entry_date"]))}</td>'
            f'<td>{float(row["shares"]):,.2f}</td>'
            f'<td>${float(row["entry_price"]):,.2f}</td>'
            f'<td>${float(row["current_price"]):,.2f}</td>'
            f'<td>${float(row["position_value"]):,.2f}</td>'
            f'<td class="{pnl_class}">${pnl:,.2f}</td>'
            f'<td class="{pnl_class}">{pnl_pct * 100:,.2f}%</td>'
            "</tr>"
        )
    header = "".join(f"<th>{label}</th>" for label in headers)
    return (
        '<div class="table-wrap"><table><thead><tr>'
        f'{header}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    )
