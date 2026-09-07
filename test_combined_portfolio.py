import unittest

import pandas as pd

from generate_combined_portfolio_page import (combine_curves, summarize, period_returns,
                                              build_comparison_chart, build_comparison_monthly_table)
from combined_portfolio_template import render_page


class CombinedPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.DatetimeIndex(["2024-01-31", "2024-02-01", "2024-02-29", "2024-03-01"], name="Date")
        self.etf = pd.DataFrame({"ETF1": [100, 110, 121, 100], "SPY_Equity": [200, 202, 220, 210]}, index=self.dates)
        self.haa = pd.DataFrame({"HAA": [2, 2, 2, 2], "60/40_Equity": [1, 1.02, 1.05, 1.03]}, index=self.dates)
        self.mr = pd.DataFrame({"Mean Reversion": [1000, 900, 810, 1000]}, index=self.dates)

    def test_independent_sleeves_and_compounding(self):
        daily = combine_curves(self.etf, self.haa, self.mr)
        self.assertEqual(daily.Equity.tolist(), [30000, 30000, 30200, 30000])
        self.assertEqual(daily.SPY_Equity.iloc[0], 30000)
        self.assertEqual(daily["60/40_Equity"].iloc[0], 30000)
        summary, monthly, months, partial = summarize(daily)
        self.assertAlmostEqual(summary.total_return, 0)
        self.assertAlmostEqual(summary.daily_max_drawdown, 30000 / 30200 - 1)
        self.assertAlmostEqual((1 + months).prod() - 1, summary.total_return)
        self.assertAlmostEqual(monthly["Year Return"].iloc[0], 0)
        self.assertEqual(partial["latest_day"], "2024-03-01")

    def test_rebase_at_shared_start(self):
        daily = combine_curves(self.etf, self.haa.iloc[1:], self.mr)
        self.assertEqual(daily.Date.iloc[0], self.dates[1])
        self.assertEqual(daily.Equity.iloc[0], 30000)
        self.assertAlmostEqual(daily.ETF1.iloc[-1], 10000 * 100 / 110)

    def test_missing_session_fails(self):
        with self.assertRaisesRegex(ValueError, "missing or mismatched"):
            combine_curves(self.etf, self.haa.drop(self.dates[1]), self.mr)

    def test_no_overlap_fails(self):
        with self.assertRaisesRegex(ValueError, "overlapping"):
            combine_curves(self.etf.iloc[:1], self.haa.iloc[2:], self.mr)

    def test_results_only_render(self):
        daily = combine_curves(self.etf, self.haa, self.mr)
        summary, monthly, months, partial = summarize(daily)
        page = render_page(summary, daily, months, monthly, {}, partial,
                           results_only=True, title="Combined Portfolio", description="Three $10,000 strategies.")
        for text in ("Combined Portfolio", "Starting equity: $30,000", "Equity Curve", "Monthly Returns"):
            self.assertIn(text, page)
        for text in ("Member Signals", "current holdings", "position-calculator", "member.js", "Historical Trades"):
            self.assertNotIn(text, page)

    def test_benchmark_returns_use_matching_periods(self):
        daily = combine_curves(self.etf, self.haa, self.mr)
        returns = period_returns(daily)
        self.assertAlmostEqual(returns.loc["2024-02", "SPY_Equity"], .10)
        self.assertAlmostEqual(returns.loc["2024-02", "60/40_Equity"], .05)
        annual = (1 + returns).prod() - 1
        self.assertAlmostEqual(annual["SPY_Equity"], .05)
        self.assertAlmostEqual(annual["60/40_Equity"], .03)
        table = build_comparison_monthly_table(daily)
        self.assertIn('SPY Return', table)
        self.assertIn('60/40 Return', table)
        self.assertIn('5.0%', table)
        self.assertIn('3.0%', table)

    def test_drawdown_uses_each_curves_running_peak(self):
        daily = combine_curves(self.etf, self.haa, self.mr)
        chart = build_comparison_chart(daily)
        self.assertEqual(len(chart.data), 6)
        for offset, column in enumerate(("Equity", "SPY_Equity", "60/40_Equity")):
            trace = chart.data[offset * 2 + 1]
            self.assertEqual(trace.yaxis, "y2")
            self.assertEqual(trace.y[0], 0)
            self.assertAlmostEqual(trace.y[-1], daily[column].iloc[-1] / daily[column].max() - 1)


if __name__ == "__main__":
    unittest.main()
