#!/usr/bin/env python3
"""Extend the completed MOMO Stocks alert with a current-month preview."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy-root", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    root = args.strategy_root.resolve()
    sys.path.insert(0, str(root))
    import update_v2a_live as live

    signal_path = root / "output_pit_v2a_live" / "latest_signal.json"
    membership = pd.read_csv(live.MEMBERSHIP_FILE, parse_dates=["date"])
    membership_date = membership["date"].max().normalize()
    latest_date = live.latest_completed_price_date()
    signal_dates = sorted(pd.Timestamp(value).normalize() for value in membership["date"].unique())
    executable_dates = [
        signal_date for signal_date in signal_dates
        if pd.bdate_range(signal_date + pd.Timedelta(days=1), periods=1)[0] <= latest_date
    ]
    if not executable_dates:
        raise RuntimeError("No completed signal has an executable MOO session")
    current_signal_date = executable_dates[-1]
    members = sorted(membership.loc[
        membership["date"].isin([membership_date, current_signal_date]), "ticker"
    ].unique())

    clean_prices, clean_audit = live.clean_live_prices(members, latest_date)
    momentum = clean_prices.pct_change(live.v2a.pit_v2.LOOKBACK_DAYS).iloc[-1]
    candidates = momentum.dropna().nlargest(150).index.tolist()
    cap_data = pd.read_csv(live.CAP_FILE, parse_dates=["date"])
    cap_data = live.update_caps_for_tickers(cap_data, candidates, latest_date)

    preview_membership = membership.loc[
        membership["date"].eq(membership_date)
    ].copy()
    preview_membership["date"] = latest_date
    preview = live.live_signal(
        clean_prices,
        preview_membership,
        cap_data,
        latest_date,
        latest_date,
    )
    next_month = (latest_date.to_period("M") + 1).to_timestamp()
    execution_date = pd.bdate_range(next_month, periods=1)[0]
    preview["execution_date"] = f"{execution_date:%Y-%m-%d}"
    preview["preliminary"] = True
    current_membership = membership.loc[
        membership["date"].eq(current_signal_date)
    ].copy()
    current_signal = live.live_signal(
        clean_prices,
        current_membership,
        cap_data,
        current_signal_date,
        latest_date,
    )
    current_holdings = current_signal.get("holdings") or [current_signal.get("defensive_holding")]
    current_holdings = [ticker for ticker in current_holdings if ticker]
    current_closes, current_opens, _ = live.v2a.pit_v2.load_price_frames(current_holdings)
    price_dates = current_closes.index[
        (current_closes.index > current_signal_date)
        & (current_closes.index <= latest_date)
    ]
    requested_entry = pd.bdate_range(
        current_signal_date + pd.Timedelta(days=1), periods=1
    )[0]
    price_dates = price_dates[
        (price_dates >= requested_entry) & (price_dates <= latest_date)
    ]
    if price_dates.empty:
        raise RuntimeError(
            f"No current-allocation prices from {requested_entry:%Y-%m-%d} through "
            f"{latest_date:%Y-%m-%d}"
        )
    entry_date = price_dates[0]
    current_price_date = price_dates[-1]
    missing_holdings = [
        ticker for ticker in current_holdings
        if ticker not in current_closes or ticker not in current_opens
    ]
    if missing_holdings:
        raise RuntimeError(
            "Current allocation is missing price history for: "
            + ", ".join(missing_holdings)
        )
    holding_returns = (
        current_closes.loc[current_price_date, current_holdings]
        / current_opens.loc[entry_date, current_holdings]
        - 1
    )
    if holding_returns.isna().any():
        missing_returns = holding_returns[holding_returns.isna()].index.tolist()
        raise RuntimeError(
            "Current allocation cannot be marked for: " + ", ".join(missing_returns)
        )
    spy_partial_return = (
        current_closes.at[current_price_date, "SPY"]
        / current_opens.at[entry_date, "SPY"]
        - 1
    )
    preview["current_allocation"] = {
        "signal_date": f"{current_signal_date:%Y-%m-%d}",
        "execution_date": f"{entry_date:%Y-%m-%d}",
        "regime": current_signal.get("regime"),
        "holdings": current_holdings,
        "latest_price_date": f"{current_price_date:%Y-%m-%d}",
        "partial_return": float(holding_returns.mean()),
        "spy_partial_return": float(spy_partial_return),
    }

    signal_path.write_text(json.dumps(preview, indent=2), encoding="utf-8")
    pd.DataFrame(preview["ranked_stocks"]).to_csv(
        signal_path.with_name("latest_ranked_stocks.csv"), index=False
    )
    clean_audit.to_csv(signal_path.with_name("preview_clean_history_audit.csv"), index=False)
    print(json.dumps(preview, indent=2))


if __name__ == "__main__":
    main()
