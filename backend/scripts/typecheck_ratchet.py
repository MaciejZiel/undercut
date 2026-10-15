"""Type-check gate that only ever tightens (NFR-501).

mypy is not used (its dependency `pathspec` is MPL-2.0); pyright is. With the Django stubs it
still reports some false positives on the ORM, so a zero-error gate is not realistic. Instead the
number of errors may never rise above the committed baseline, and a lower number asks for the
baseline to be lowered, so the count only goes down.

Usage: python scripts/typecheck_ratchet.py [--update]   (run from backend/)
"""

import json
import subprocess
import sys
from pathlib import Path

BASELINE = Path(__file__).with_name("pyright-baseline.txt")


def count_errors() -> int:
    result = subprocess.run(
        ["pyright", "--outputjson"], capture_output=True, text=True, check=False
    )  # noqa: S603, S607
    report = json.loads(result.stdout)
    return int(report["summary"]["errorCount"])


def main() -> int:
    current = count_errors()
    if "--update" in sys.argv:
        BASELINE.write_text(f"{current}\n")
        print(f"baseline set to {current}")
        return 0
    allowed = int(BASELINE.read_text().strip())
    if current > allowed:
        print(
            f"pyright reports {current} errors, baseline is {allowed}: new type errors were added"
        )
        return 1
    if current < allowed:
        print(f"pyright reports {current} errors, below the baseline {allowed}: run with --update")
        return 1
    print(f"pyright: {current} errors, same as the baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
