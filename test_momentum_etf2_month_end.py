import unittest

import pandas as pd

from generate_momentum_etf2_page import extend_daily_to_partial, latest_alert_table


class MonthEndTransitionTests(unittest.TestCase):
    def setUp(self):
        self.days = pd.to_datetime(["2026-08-03", "2026-09-01", "2026-09-30"])
        self.close = pd.DataFrame(
            {"XLK": [100.0, 105.0, 110.0], "XLE": [50.0, 51.0, 54.0], "SPY": [600.0, 610.0, 620.0]},
            index=self.days,
        )
        self.open = pd.DataFrame(
            {"XLK": [99.0, 104.0, 109.0], "XLE": [49.0, 50.0, 53.0], "SPY": [599.0, 609.0, 619.0]},
            index=self.days,
        )
        self.daily = pd.DataFrame(
            {"holding": ["XLK"], "strategy_wealth": [2.0], "spy_wealth": [1.5], "switched": [False]},
            index=pd.to_datetime(["2026-09-01"]),
        )
        self.monthly = pd.DataFrame(
            {"held": ["XLK"], "entry_date": ["2026-08-03"], "exit_date": ["2026-09-01"]},
            index=["2026-08"],
        )
        self.alert = {
            "signal_month_end": "2026-09",
            "effective_month": "2026-10",
            "current_holding": "XLE",
            "next_holding": "XLE",
            "allocation_changed": False,
        }

    def test_signal_day_keeps_current_holding_until_next_open(self):
        extended, partial, _, positions = extend_daily_to_partial(
            self.daily, self.close, self.open, self.alert, 200000.0, self.monthly
        )
        self.assertEqual(extended.iloc[-1]["holding"], "XLE")
        self.assertAlmostEqual(partial, (1 - .001) * 54 / 50 - 1)
        self.assertEqual(positions[0]["ticker"], "XLE")

    def test_new_signal_is_pending_without_completed_backtest_row(self):
        html = latest_alert_table(self.daily, self.alert, self.monthly, self.close)
        self.assertIn("2026-10-01 open", html)
        self.assertIn("Pending next-session open", html)


if __name__ == "__main__":
    unittest.main()
