"""Next-session long-only MOO orders from completed cached bars, never future fills."""
import argparse
import html
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def session_dates(now=None):
    import pandas_market_calendars as mcal
    now = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="America/New_York")
    if now.tzinfo is None:
        raise ValueError("The current time must include a timezone")
    schedule = mcal.get_calendar("NYSE").schedule(
        start_date=(now - pd.Timedelta(days=14)).date(),
        end_date=(now + pd.Timedelta(days=14)).date())
    completed = schedule.loc[schedule.market_close <= now].index[-1]
    execution = schedule.index[schedule.index > completed][0]
    return completed, execution


def latest_signal(bars, cfg):
    """Same indicator formulas as RevMurphy; calculate rolling ranks only at the last bar."""
    from indicators import rsi
    bars = bars.sort_values("date").reset_index(drop=True)
    close = bars.close
    row = bars.iloc[-1]
    returns = close.pct_change(cfg.QPI_RETURN_DAYS)
    prior = returns.shift(1).tail(cfg.QPI_LOOKBACK_DAYS)
    qpi = float((prior <= returns.iloc[-1]).mean()) if len(prior) == cfg.QPI_LOOKBACK_DAYS and prior.notna().all() and pd.notna(returns.iloc[-1]) else np.nan
    span = row.high - row.low
    ibs = float(np.clip((row.close - row.low) / span, 0, 1)) if span else np.nan
    rsi2 = float(rsi(close, cfg.RSI_LOOKBACK_DAYS).iloc[-1])
    volume_max = bars.volume.shift(1).rolling(cfg.VOLUME_FILTER_LOOKBACK_DAYS, min_periods=cfg.VOLUME_FILTER_LOOKBACK_DAYS).max().iloc[-1]
    volume_skip = cfg.USE_VOLUME_FILTER and pd.notna(volume_max) and row.volume > volume_max
    prior_daily = close.pct_change().shift(1).tail(cfg.CVAR_LOOKBACK_DAYS)
    cvar = prior_daily.nsmallest(max(1, int(np.ceil(len(prior_daily) * cfg.CVAR_TAIL_FRACTION)))).mean() if len(prior_daily) == cfg.CVAR_LOOKBACK_DAYS and prior_daily.notna().all() else np.nan
    cvar_skip = cfg.USE_CVAR_FILTER and (pd.isna(cvar) or cvar < cfg.MIN_CVAR_5PCT)
    entry = (close.pct_change(cfg.DROP_LOOKBACK_DAYS).iloc[-1] < cfg.DROP_THRESHOLD
             and qpi < cfg.QPI_THRESHOLD
             and row.close > close.rolling(cfg.SMA_LOOKBACK_DAYS, min_periods=cfg.SMA_LOOKBACK_DAYS).mean().iloc[-1]
             and ibs < cfg.ENTRY_IBS_THRESHOLD and not volume_skip and not cvar_skip)
    return dict(close=float(row.close), qpi=qpi, ibs=ibs, rsi2=rsi2,
                entry_signal=bool(entry), exit_signal=bool(ibs > cfg.EXIT_IBS_THRESHOLD or rsi2 > cfg.EXIT_RSI2_THRESHOLD))


def select_orders(day, positions, cash, execution, cost_rate=.0005, max_hold_days=None):
    if len(positions) > 5 or (not positions.empty and not positions.side.eq("long").all()):
        raise ValueError("Expected the production long-only five-position portfolio")
    missing = set(positions.ticker) - set(day.index)
    if missing:
        raise ValueError(f"Missing current bars for held positions: {sorted(missing)}")
    orders, retained = [], []
    for pos in positions.itertuples():
        row = day.loc[pos.ticker]
        aged = max_hold_days is not None and (execution - pd.Timestamp(pos.entry_date)).days >= max_hold_days
        if execution > pd.Timestamp(pos.entry_date) and (row.exit_signal or aged):
            proceeds = float(pos.shares * row.close)
            cash += proceeds * (1 - cost_rate)
            orders.append(dict(action="Exit", ticker=pos.ticker, shares=float(pos.shares),
                               estimated_notional=proceeds, reference_close=float(row.close),
                               reason="Maximum holding period" if aged else "Exit signal"))
        else:
            retained.append(pos)
    equity = cash + sum(pos.shares * day.loc[pos.ticker, "close"] for pos in retained)
    held = {pos.ticker for pos in retained}
    candidates = day.loc[day.entry_signal & ~day.index.isin(held)].sort_values(["qpi", "ibs"]).head(5-len(retained))
    for ticker, row in candidates.iterrows():
        notional = min(equity / 5, cash / (1 + cost_rate))
        if notional <= 0:
            continue
        cash -= notional * (1 + cost_rate)
        orders.append(dict(action="Buy", ticker=ticker, shares=float(notional / row.close),
                           estimated_notional=float(notional), reference_close=float(row.close),
                           reason="Ranked entry signal"))
    return orders


def render_orders(payload, results_through):
    signal = pd.Timestamp(payload["signal_date"])
    execution = pd.Timestamp(payload["execution_date"])
    if signal != pd.Timestamp(results_through).normalize() or execution <= signal:
        raise ValueError("Next-session orders do not match the backtest reporting date")
    rows = []
    for order in payload["orders"]:
        quantity = f'{order["shares"]:,.2f}' if order["action"] == "Exit" else f'~{order["shares"]:,.2f}'
        rows.append(f'<tr><td>{html.escape(order["action"])}</td><td>{html.escape(order["ticker"])}</td>'
                    f'<td>{quantity}</td><td>${order["estimated_notional"]:,.0f}</td>'
                    f'<td>${order["reference_close"]:,.2f}</td><td>Pending market open</td></tr>')
    if not rows:
        rows = ['<tr><td colspan="6">No orders for this session; retain current positions.</td></tr>']
    stale = payload.get("excluded_stale_tickers", [])
    coverage = ('<p class="subtle">Excluded from new entries because their latest bars are older than the signal date: '
                + html.escape(', '.join(stale)) + '.</p>') if stale else ''
    return (f'<p class="subtle">Signal date: {signal:%Y-%m-%d} (completed close) · MOO execution date: {execution:%Y-%m-%d}.</p>'
            '<p class="subtle">Exits execute before new entries. Buy quantities and values are estimates using the signal-day close and 5 bps per side. '
            'Actual sizing depends on opening equity, available cash, and opening prices. Fill prices are not yet known.</p>'
            + coverage + '<div class="table-wrap"><table><thead><tr><th>Action</th><th>Ticker</th><th>Shares (buys estimated)</th>'
            '<th>Estimated Value</th><th>Reference Close</th><th>Execution</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy-root", type=Path, default=Path("C:/junk/stocks/RevMurphy"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--price-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.strategy_root))
    import config
    signal_date, execution = session_dates()
    equity = pd.read_csv(args.source / "equity_curve.csv", parse_dates=["date"])
    if equity.iloc[-1].date != signal_date:
        raise ValueError(f"Backtest must reach latest completed session {signal_date.date()}")
    trades = pd.read_csv(args.source / "trades.csv")
    positions = trades.loc[trades.status.eq("open")]
    # Use the exact universe included in this backtest, without another network request.
    tickers = set()
    for chunk in pd.read_csv(args.source / "all_signals.csv", usecols=["ticker"], chunksize=100000):
        tickers.update(chunk.ticker)
    rows, stale = [], []
    for ticker in sorted(tickers):
        bars = pd.read_csv(args.price_source / f"{ticker}.csv", parse_dates=["date"])
        bars = bars.loc[bars.date <= signal_date]
        if bars.empty or bars.date.max() != signal_date:
            stale.append(ticker)
            continue
        rows.append(dict(ticker=ticker, **latest_signal(bars, config)))
    if not rows:
        raise ValueError("No current signal bars")
    day = pd.DataFrame(rows).set_index("ticker")
    orders = select_orders(day, positions, float(equity.iloc[-1].cash), execution,
                           config.TRANSACTION_COST_BPS / 10000, config.MAX_HOLD_DAYS)
    payload = dict(signal_date=str(signal_date.date()), execution_date=str(execution.date()),
                   generated_at=pd.Timestamp.now(tz="UTC").isoformat(), orders=orders,
                   evaluated_tickers=len(rows), excluded_stale_tickers=stale)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding="utf-8")
    print(f'Next-session MOO orders: {signal_date.date()} -> {execution.date()}; {len(orders)} orders; {len(rows)} current tickers; {len(stale)} stale tickers excluded.')


if __name__ == "__main__":
    main()
