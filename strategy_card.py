from pathlib import Path


def _update_card_stats(path: Path, title: str, stats_class: str, stats: str):
    text = path.read_text(encoding="utf-8")
    card_start = text.index(f"<h2>{title}</h2>")
    card_end = text.index("</div>", card_start)
    stats_start = text.index(f'<p class="{stats_class}">', card_start, card_end)
    stats_end = text.index("</p>", stats_start, card_end) + len("</p>")
    path.write_text(text[:stats_start] + stats + text[stats_end:], encoding="utf-8")


def update_backtest_card(
    path: Path,
    title: str,
    cagr: float,
    sharpe: float,
    max_drawdown: float,
    spy_max_drawdown: float,
):
    """Replace only the statistics block for one strategy overview card."""
    stats = (
        '<p class="card-stats">\n'
        f'<span class="positive">{float(cagr) * 100:.1f}% Backtest CAGR</span>\n'
        f'<span class="positive">{float(sharpe):.2f} Sharpe Ratio</span>\n'
        f'<span class="negative">{float(max_drawdown) * 100:.1f}% Max Drawdown</span>\n'
        f'<span class="negative">{float(spy_max_drawdown) * 100:.1f}% SPY Max Drawdown</span>\n'
        "</p>"
    )
    _update_card_stats(path, title, "card-stats", stats)


def update_member_backtest_card(
    path: Path,
    title: str,
    cagr: float,
    sharpe: float,
    max_drawdown: float,
    spy_max_drawdown: float,
):
    """Keep the authenticated strategy-directory card synchronized."""
    stats = (
        '<p class="home-stats">'
        f'<span class="positive">{float(cagr) * 100:.1f}% Backtest CAGR</span>'
        f'<span class="positive">{float(sharpe):.2f} Sharpe Ratio</span>'
        f'<span class="negative">{float(max_drawdown) * 100:.1f}% Max Drawdown</span>'
        f'<span class="negative">{float(spy_max_drawdown) * 100:.1f}% SPY Max Drawdown</span>'
        "</p>"
    )
    _update_card_stats(path, title, "home-stats", stats)


def update_member_live_card(
    path: Path,
    title: str,
    cagr: str,
    sharpe: str,
    max_drawdown: str,
    max_drawdown_since_2013: str,
):
    """Keep the authenticated live-strategy directory card synchronized."""
    stats = (
        '<p class="home-stats">'
        f'<span class="positive">{cagr} CAGR</span>'
        f'<span class="positive">{sharpe} Sharpe Ratio</span>'
        f'<span class="negative">{max_drawdown} Max DD</span>'
        f'<span class="negative">{max_drawdown_since_2013} Max DD Since 2013</span>'
        "</p>"
    )
    _update_card_stats(path, title, "home-stats", stats)
