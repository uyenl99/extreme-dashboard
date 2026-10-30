import tempfile
import unittest
from pathlib import Path

import pandas as pd

from generate_momentum_page import (
    build_allocation_table,
    calculate_partial_spy_return,
    parse_alert,
)


class MomentumAlertDateTests(unittest.TestCase):
    def test_next_entry_event_supplies_exact_execution_date(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            alert = root / "next_entry_alert.txt"
            alert.write_text(
                "Signal month : 2026-09\nExecute at : 2026-10 open\nHoldings : SMH, GDX, XLE\n",
                encoding="utf-8",
            )
            events = root / "alerts.csv"
            events.write_text(
                'severity,type,date,message\nINFO,NEXT_ENTRY,2026-10-01,"Next entry"\n',
                encoding="utf-8",
            )

            parsed = parse_alert(alert, events)

        self.assertEqual(parsed["Execution"], "2026-10-01 open")

    def test_weekend_month_marker_moves_to_next_nyse_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            alert = root / "next_entry_alert.txt"
            alert.write_text(
                "Signal month : 2026-10\nExecute at : 2026-11 open\nHoldings : SMH, XLE, XLK\n",
                encoding="utf-8",
            )
            events = root / "alerts.csv"
            events.write_text(
                'severity,type,date,message\nINFO,NEXT_ENTRY,2026-11-01,"Next entry"\n',
                encoding="utf-8",
            )

            parsed = parse_alert(alert, events)

        self.assertEqual(parsed["Execution"], "2026-11-02 open")

    def test_partial_spy_uses_entry_open_and_latest_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "output_momo5"
            data = root / "data"
            source.mkdir()
            data.mkdir()
            pd.DataFrame(
                [
                    {"date": "2026-10-01", "open": 100.0, "close": 101.0},
                    {"date": "2026-10-30", "open": 99.0, "close": 98.0},
                ]
            ).to_csv(data / "SPY_daily.csv", index=False)
            partial = pd.Series({"entry_day": "2026-10-01", "latest_day": "2026-10-30"})

            result = calculate_partial_spy_return(source, partial)

        self.assertAlmostEqual(result, -0.02)

    def test_partial_history_displays_spy_return(self):
        partial = pd.Series(
            {
                "risk_off": False,
                "partial_return": -0.040275,
                "spy_partial_return": -0.011304,
                "entry_month": "2026-10-01",
                "latest_day": "2026-10-30",
                "holdings": "SMH, GDX, XLE",
            }
        )
        history = pd.DataFrame(
            columns=["date", "exit_date", "h1", "h2", "h3", "risk_off", "port_ret", "spy_ret"]
        )

        rendered = build_allocation_table(history, partial)

        self.assertIn("-4.03%", rendered)
        self.assertIn("-1.13%", rendered)


if __name__ == "__main__":
    unittest.main()
