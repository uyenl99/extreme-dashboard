from pathlib import Path


def update_backtest_card(
    path: Path,
    title: str,
    cagr: float,
    sharpe: float,
    max_drawdown: float,
    spy_max_drawdown: float,
):
    """Replace only the statistics block for one strategy overview card."""
    text = path.read_text(encoding="utf-8")
    card_start = text.index(f"<h2>{title}</h2>")
    card_end = text.index("</div>", card_start)
    stats_start = text.index('<p class="card-stats">', card_start, card_end)
    stats_end = text.index("</p>", stats_start, card_end) + len("</p>")
    stats = (
        '<p class="card-stats">\n'
        f'<span class="positive">{float(cagr) * 100:.1f}% Backtest CAGR</span>\n'
        f'<span class="positive">{float(sharpe):.2f} Sharpe Ratio</span>\n'
        f'<span class="negative">{float(max_drawdown) * 100:.1f}% Max Drawdown</span>\n'
        f'<span class="negative">{float(spy_max_drawdown) * 100:.1f}% SPY Max Drawdown</span>\n'
        "</p>"
    )
    path.write_text(text[:stats_start] + stats + text[stats_end:], encoding="utf-8")
