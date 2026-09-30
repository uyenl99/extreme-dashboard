import tempfile
import unittest
from pathlib import Path

from generate_momentum_page import parse_alert


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


if __name__ == "__main__":
    unittest.main()
