import argparse
from pathlib import Path

SCRIPT = '<script src="/position-calculator.js" defer></script>'

parser = argparse.ArgumentParser()
parser.add_argument("pages", nargs="+", type=Path)
args = parser.parse_args()
for page in args.pages:
    text = page.read_text(encoding="utf-8")
    if SCRIPT not in text:
        page.write_text(text.replace("</body>", f"{SCRIPT}</body>"), encoding="utf-8")
    print(f"Position calculator enabled: {page}")
