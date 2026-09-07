"""Fail before daily runs if a local production engine differs from the approved rerun."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path("C:/junk/stocks")


def source_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main():
    manifest = json.loads((ROOT / "research/transaction-costs-5bps/engine_versions.json").read_text())
    failures = []
    for name, expected in manifest.items():
        path = SOURCE_ROOT / name
        if not path.is_file() or source_hash(path) != expected:
            failures.append(name)
    if failures:
        raise SystemExit("Backtest engine version mismatch: " + ", ".join(failures)
                         + ". Restore the approved sources or validate and commit a new version manifest before publishing.")
    print(f"Approved 5-bps backtest engine versions verified ({len(manifest)} files).")


if __name__ == "__main__":
    main()
