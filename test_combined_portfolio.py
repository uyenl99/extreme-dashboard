import unittest
import tempfile
from pathlib import Path

import pandas as pd

from generate_combined_portfolio_page import (combine_curves, summarize, period_returns,
                                              build_comparison_chart, build_comparison_monthly_table, extend_etf1, extend_haa)
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

    def test_current_month_is_labeled_and_included_in_annual_returns(self):
        daily=combine_curves(self.etf,self.haa,self.mr)
        table=build_comparison_monthly_table(daily)
        self.assertIn('Partial month-to-date through 2024-03-01',table)
        self.assertIn('-0.7%*',table)
        self.assertIn('annual returns include this partial month',table)

    def test_etf_partial_daily_marks_reconcile_and_keep_completed_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'output'; source.mkdir(); (root/'data').mkdir()
            pd.DataFrame([dict(entry_day='2024-03-01',latest_day='2024-03-04',cost_fraction=.001,partial_return=1.2*.999-1)]).to_csv(source/'partial_month_return.csv',index=False)
            pd.DataFrame([dict(ticker='A',entry_price=100)]).to_csv(source/'partial_month_slots.csv',index=False)
            for ticker,values in [('A',[100,110,120]),('SPY',[200,202,204])]:
                pd.DataFrame(dict(date=['2024-02-29','2024-03-01','2024-03-04'],close=values)).to_csv(root/'data'/f'{ticker}_daily.csv',index=False)
            base=self.etf.iloc[:3]
            extended=extend_etf1(base,source)
            pd.testing.assert_frame_equal(extended.iloc[:3],base,check_dtype=False)
            self.assertAlmostEqual(extended.ETF1.iloc[-1],121*1.2*.999)
            self.assertAlmostEqual(extended.SPY_Equity.iloc[-1],220*1.02)
            self.assertEqual(len(extended),5)

    def test_haa_current_marks_require_matching_base(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)
            frame=pd.DataFrame({'Date':['2024-03-01','2024-03-04'],'HAA net 5bp':[2,2.1],'60 SPY 40 IEF':[1.03,1.04]})
            frame.to_csv(source/'current_daily_equity.csv',index=False)
            extended=extend_haa(self.haa,source)
            self.assertAlmostEqual(extended.HAA.iloc[-1],2.1)
            frame.loc[0,'HAA net 5bp']=99
            frame.to_csv(source/'current_daily_equity.csv',index=False)
            with self.assertRaises(ValueError): extend_haa(self.haa,source)


if __name__ == "__main__":
    unittest.main()
