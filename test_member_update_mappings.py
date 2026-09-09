import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from generate_haa_page import allocation_history as haa_allocation_history
from generate_momentum_etf2_page import (
    allocation_history as etf2_allocation_history,
    extend_daily_to_partial,
)


class Etf2MemberUpdateTests(unittest.TestCase):
    def test_completed_signal_becomes_current_month_holding(self):
        daily = pd.DataFrame(
            {"holding": ["XLK"], "strategy_wealth": [2.0], "spy_wealth": [1.5]},
            index=pd.to_datetime(["2026-08-31"]),
        )
        prices_index = pd.to_datetime(["2026-08-03", "2026-09-01", "2026-09-02"])
        close = pd.DataFrame(
            {"XLK": [90.0, 101.0, 102.0], "XLE": [95.0, 100.0, 110.0], "SPY": [95.0, 100.0, 105.0]},
            index=prices_index,
        )
        opens = pd.DataFrame(
            {"XLK": [90.0, 100.0, 101.0], "XLE": [95.0, 100.0, 109.0], "SPY": [95.0, 100.0, 104.0]},
            index=prices_index,
        )
        monthly = pd.DataFrame(
            {"held": ["XLK"], "entry_date": ["2026-08-03"], "exit_date": ["2026-09-01"]},
            index=["2026-08"],
        )
        alert = {
            "signal_month_end": "2026-08",
            "effective_month": "2026-09",
            "current_holding": "XLK",
            "next_holding": "XLE",
        }

        _, partial, spy, positions = extend_daily_to_partial(
            daily, close, opens, alert, 200000.0, monthly
        )

        self.assertEqual([position["ticker"] for position in positions], ["XLE"])
        self.assertAlmostEqual(partial, (1 - 0.001) * 1.1 - 1)
        self.assertAlmostEqual(spy, 0.05)

    def test_open_month_is_newest_of_twenty_rows(self):
        months = pd.period_range("2025-01", periods=20, freq="M")
        history = pd.DataFrame(
            {"held": ["XLK"] * 20, "strategy_return": [0.01] * 20, "spy_return": [0.005] * 20},
            index=months.astype(str),
        )
        current = {"Month": "2026-09", "Holdings": "XLE", "Return": 0.02, "SPY": 0.01, "Status": "Open"}
        result = etf2_allocation_history(history, current)
        self.assertEqual(len(result), 20)
        self.assertEqual(result.iloc[0]["Month"], "2026-09")
        self.assertEqual(result.iloc[0]["Holdings"], "XLE")


class HaaMemberUpdateTests(unittest.TestCase):
    def test_history_uses_execution_month_not_calendar_month_end(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            pd.DataFrame(
                [
                    {"signal_date": "2026-04-30", "date": "2026-05-01", "SPY": 1.0, "IEF": 0.0},
                    {"signal_date": "2026-05-29", "date": "2026-06-01", "SPY": 0.0, "IEF": 1.0},
                ]
            ).to_csv(source / "exact_etfs_HAA_net_5bp_trades.csv", index=False)
            returns = pd.DataFrame(
                {"HAA net 5bp": [0.01, 0.02], "SPY": [0.03, 0.04]},
                index=pd.to_datetime(["2026-05-31", "2026-06-30"]),
            )
            targets = pd.DataFrame(
                {"SPY": [1.0, 0.0], "IEF": [0.0, 1.0]},
                index=pd.to_datetime(["2026-04-30", "2026-05-29"]),
            )
            snapshot = {"pending": True}

            result = haa_allocation_history(source, returns, targets, snapshot)

            june = result.loc[result["Month"].eq("2026-06")].iloc[0]
            may = result.loc[result["Month"].eq("2026-05")].iloc[0]
            self.assertEqual(june["Signal"], "2026-05-29")
            self.assertEqual(june["Holdings"], "IEF 100%")
            self.assertEqual(may["Signal"], "2026-04-30")
            self.assertEqual(may["Holdings"], "SPY 100%")


if __name__ == "__main__":
    unittest.main()
