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
    completed = json.loads(signal_path.read_text(encoding="utf-8"))
    membership = pd.read_csv(live.MEMBERSHIP_FILE, parse_dates=["date"])
    membership_date = membership["date"].max().normalize()
    latest_date = pd.Timestamp.now().normalize() - pd.offsets.BDay(1)
    members = sorted(
        membership.loc[membership["date"].eq(membership_date), "ticker"].unique()
    )

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
    preview["current_allocation"] = {
        "signal_date": completed.get("signal_date"),
        "execution_date": completed.get("execution_date"),
        "regime": completed.get("regime"),
        "holdings": completed.get("holdings") or [completed.get("defensive_holding")],
    }

    signal_path.write_text(json.dumps(preview, indent=2), encoding="utf-8")
    pd.DataFrame(preview["ranked_stocks"]).to_csv(
        signal_path.with_name("latest_ranked_stocks.csv"), index=False
    )
    clean_audit.to_csv(signal_path.with_name("preview_clean_history_audit.csv"), index=False)
    print(json.dumps(preview, indent=2))


if __name__ == "__main__":
    main()
