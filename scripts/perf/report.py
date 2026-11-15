"""Turn the JSON lines written by load_test.py --json into a Markdown table.

    python scripts/perf/report.py results.jsonl > summary.md
"""

import json
import sys


def main(path: str) -> int:
    with open(path, encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    print("| Path | Requests/s | p50 ms | p95 ms | p99 ms | Errors |")
    print("|---|---:|---:|---:|---:|---:|")
    for row in rows:
        print(
            f"| `{' '.join(row['paths'])}` | {row['rps']:.0f} | {row['p50_ms']:.0f} "
            f"| {row['p95_ms']:.0f} | {row['p99_ms']:.0f} | {row['errors']} |"
        )
    if rows:
        print(f"\n{rows[0]['connections']} connections, {rows[0]['seconds']} s per path.")
    return 0 if all(row["ok"] for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
