#!/usr/bin/env python3
"""Fail unless every published backtest uses the documented MOO execution price."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd


STOCKS = Path(r"C:\junk\stocks")
ETF1 = STOCKS / "DualMom"
ETF2 = STOCKS / "inflationcompass"
MOMO_SP = STOCKS / "MomoSp" / "pit_version"
MEAN_REVERSION = STOCKS / "RevMurphy"
WEB = Path(__file__).resolve().parents[1]
TOLERANCE = 1e-8


def assert_close(actual: pd.Series, expected: pd.Series, label: str) -> None:
    difference = (actual.astype(float) - expected.astype(float)).abs()
    if difference.isna().any() or float(difference.max()) > TOLERANCE:
        bad = difference.sort_values(ascending=False).head(5)
        raise AssertionError(f"{label} does not reconcile to MOO prices:\n{bad}")


def verify_etf1() -> int:
    results = pd.read_csv(
        ETF1 / "output_momo5" / "dual_momentum_results.csv",
        parse_dates=["date", "exit_date"],
    )
    if set(results["execution_price"]) != {"adjusted_open"}:
        raise AssertionError("ETF1 output is not tagged adjusted_open")

    tickers = sorted(set(results[["h1", "h2", "h3"]].stack()) | {"SPY"})
    opens = {}
    for ticker in tickers:
        frame = pd.read_csv(ETF1 / "data" / f"{ticker}_daily.csv", parse_dates=["date"])
        opens[ticker] = frame.set_index("date")["open"]
    monthly_open = pd.DataFrame(opens).resample("MS").first()

    expected = []
    for row in results.itertuples(index=False):
        expected.append(
            np.mean(
                [
                    monthly_open.at[row.exit_date, ticker]
                    / monthly_open.at[row.date, ticker]
                    - 1
                    for ticker in (row.h1, row.h2, row.h3)
                ]
            )
        )
    assert_close(results["port_ret"], pd.Series(expected), "ETF1 strategy return")
    expected_spy = pd.Series(
        [
            monthly_open.at[row.exit_date, "SPY"]
            / monthly_open.at[row.date, "SPY"]
            - 1
            for row in results.itertuples(index=False)
        ]
    )
    assert_close(results["spy_ret"], expected_spy, "ETF1 SPY return")
    return len(results)


def verify_etf2() -> int:
    output = ETF2 / "output"
    results = pd.read_csv(output / "monthly_backtest.csv")
    opens = pd.read_csv(output / "adjusted_open_prices.csv", index_col=0, parse_dates=True)
    if set(results["execution_price"]) != {"adjusted_open"}:
        raise AssertionError("ETF2 output is not tagged adjusted_open")
    results["entry_date"] = pd.to_datetime(results["entry_date"])
    results["exit_date"] = pd.to_datetime(results["exit_date"])

    expected = []
    for row in results.itertuples(index=False):
        holdings = ("XLP", "IEF") if row.held == "XLP/IEF" else (row.held,)
        expected.append(
            np.mean(
                [
                    opens.at[row.exit_date, ticker]
                    / opens.at[row.entry_date, ticker]
                    - 1
                    for ticker in holdings
                ]
            )
        )
    assert_close(results["strategy_return"], pd.Series(expected), "ETF2 strategy return")
    expected_spy = pd.Series(
        [
            opens.at[row.exit_date, "SPY"] / opens.at[row.entry_date, "SPY"] - 1
            for row in results.itertuples(index=False)
        ]
    )
    assert_close(results["spy_return"], expected_spy, "ETF2 SPY return")
    return len(results)


def verify_momo_sp() -> int:
    results = pd.read_csv(
        MOMO_SP / "output_pit_r1000_5b_latest" / "monthly_results.csv",
        parse_dates=["entry_date", "exit_date"],
    )
    if set(results["execution_price"]) != {"open"}:
        raise AssertionError("Momentum Stocks output is not tagged open")

    tickers = set(results["holdings"].str.split(",").explode()) | {"SPY"}
    sys.path.insert(0, str(MOMO_SP))
    import pit_v2

    _, opens, _ = pit_v2.load_price_frames(sorted(tickers))
    expected = []
    for row in results.itertuples(index=False):
        expected.append(
            np.mean(
                [
                    opens.at[row.exit_date, ticker]
                    / opens.at[row.entry_date, ticker]
                    - 1
                    for ticker in row.holdings.split(",")
                ]
            )
        )
    assert_close(results["gross_return"], pd.Series(expected), "Momentum Stocks gross return")
    expected_spy = pd.Series(
        [
            opens.at[row.exit_date, "SPY"] / opens.at[row.entry_date, "SPY"] - 1
            for row in results.itertuples(index=False)
        ]
    )
    assert_close(results["spy_return"], expected_spy, "Momentum Stocks SPY return")
    return len(results)


def verify_mean_reversion() -> int:
    output = MEAN_REVERSION / "output_long_short_5x5_walk_forward_next_open"
    signals = pd.read_csv(output / "all_signals.csv", parse_dates=["date", "signal_date"])
    trades = pd.read_csv(output / "trades.csv", parse_dates=["entry_date", "exit_date"])
    selections = pd.read_csv(output / "cluster_walk_forward_selection.csv")
    if not np.allclose(signals["trade_close"], signals["open"], rtol=0, atol=TOLERANCE):
        raise AssertionError("Mean Reversion trade_close differs from the daily open")
    if not (signals["signal_date"] < signals["date"]).all():
        raise AssertionError("Mean Reversion contains a signal that was not shifted to a later session")
    for row in selections.itertuples(index=False):
        expected_end = f"{int(row.selection_year) - 1}-12-31"
        if row.training_end != expected_end:
            raise AssertionError(
                f"Mean Reversion selection {row.selection_year} used {row.training_end}, expected {expected_end}"
            )
        year_rows = signals[signals["date"].dt.year == int(row.selection_year)]
        actual = set(
            zip(
                year_rows["cluster_lookback_days"].astype(int),
                year_rows["cluster_threshold"].astype(float),
                year_rows["max_per_cluster"].astype(int),
            )
        )
        expected = {
            (
                int(row.cluster_lookback_days),
                float(row.cluster_threshold),
                int(row.max_per_cluster),
            )
        }
        if actual != expected:
            raise AssertionError(
                f"Mean Reversion execution year {row.selection_year} uses {actual}, expected {expected}"
            )
    lookup = signals.set_index(["date", "ticker"])["open"]
    for row in trades.itertuples(index=False):
        if abs(float(row.entry_price) - float(lookup.at[(row.entry_date, row.ticker)])) > TOLERANCE:
            raise AssertionError(f"Mean Reversion entry is not MOO: {row.ticker} {row.entry_date}")
        if row.status == "closed" and abs(
            float(row.exit_price) - float(lookup.at[(row.exit_date, row.ticker)])
        ) > TOLERANCE:
            raise AssertionError(f"Mean Reversion exit is not MOO: {row.ticker} {row.exit_date}")
    return len(trades)


def verify_current_chart_dates() -> int:
    """Ensure partial-month chart endpoints match the latest available marks."""
    etf2_prices = pd.read_csv(
        ETF2 / "output" / "adjusted_close_prices.csv", index_col=0, parse_dates=True
    )
    etf2_date = f"{pd.Timestamp(etf2_prices.index.max()):%Y-%m-%d}"
    stock_signal = json.loads(
        (MOMO_SP / "output_pit_v2a_live" / "latest_signal.json").read_text(
            encoding="utf-8"
        )
    )
    current = stock_signal.get("current_allocation")
    if not current or not current.get("latest_price_date"):
        raise AssertionError("Momentum Stocks alert is missing current_allocation")
    stock_date = str(current["latest_price_date"])

    pages = (
        (WEB / "momentum2.html", "momoetf2-equity-chart", etf2_date),
        (WEB / "api" / "_member-content" / "momentum2.html", "momoetf2-equity-chart", etf2_date),
        (WEB / "momentum-stocks.html", "momentum-stocks-equity-chart", stock_date),
        (
            WEB / "api" / "_member-content" / "momentum-stocks.html",
            "momentum-stocks-equity-chart",
            stock_date,
        ),
    )
    for page, chart_id, endpoint in pages:
        text = page.read_text(encoding="utf-8")
        chart = re.search(
            rf'Plotly\.newPlot\(\s*"{re.escape(chart_id)}"(?P<body>.*?)</script>',
            text,
            re.DOTALL,
        )
        if not chart or endpoint not in chart.group("body"):
            raise AssertionError(f"{page.name} chart does not reach {endpoint}")
    return len(pages)


def main() -> None:
    checks = {
        "Momentum ETF1 monthly periods": verify_etf1(),
        "Momentum ETF2 monthly periods": verify_etf2(),
        "Momentum Stocks monthly periods": verify_momo_sp(),
        "Mean Reversion trades": verify_mean_reversion(),
        "Current public/member chart endpoints": verify_current_chart_dates(),
    }
    for label, count in checks.items():
        print(f"PASS {label}: {count:,}")
    print("PASS all published backtests reconcile to documented MOO execution prices")


if __name__ == "__main__":
    main()
