"""
Automation runner for the orchestrator /invoke endpoint.

Reads a CSV of (queries, step) rows, POSTs each row to the orchestrator
sharing a single session UUID across the whole run (so the orchestrator's
multi-turn memory threads them as one conversation), and writes every
response to a timestamped .txt file under `responses/`. Each block is
separated by a line of `=`.

Usage:
    python run_automation.py
    python run_automation.py --csv testscripts1.csv --output my_run.txt
    python run_automation.py --url http://localhost:8002/invoke --timeout 60
    python run_automation.py --limit 3                       # first 3 rows only
    python run_automation.py --session-id 1234-...           # reuse a specific session
"""

import argparse
import csv
import datetime
import json
import sys
import time
import uuid
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request


SEPARATOR = "=" * 80
DEFAULT_URL = "http://localhost:8002/invoke"
# DEFAULT_URL = "https://nraif-671b-dev-api.icymushroom-bc5ec66d.canadacentral.azurecontainerapps.io/invoke"
HERE = Path(__file__).parent


def post_invoke(url: str, payload: dict, timeout: float) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def format_block(
    query: str,
    step: str,
    session_id: str,
    status: int,
    body: str,
    elapsed: float,
) -> str:
    try:
        pretty = json.dumps(json.loads(body), indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        pretty = body

    return (
        f"{SEPARATOR}\n"
        f"QUERY:      {query}\n"
        f"STEP:       {step}\n"
        f"SESSION_ID: {session_id}\n"
        f"STATUS:     {status}\n"
        f"ELAPSED:    {elapsed:.2f}s\n"
        f"{SEPARATOR}\n"
        f"{pretty}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        default=str(HERE / "testscripts1.csv"),
        help="Input CSV with `queries` and `step` columns.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Orchestrator invoke URL.")
    parser.add_argument(
        "--output",
        default=None,
        help="Output .txt path. Defaults to responses/run-<timestamp>.txt next to this script.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout per request in seconds.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Send only the first N rows (handy for smoke tests).",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Override the session UUID. Defaults to a fresh uuid4 used for every row.",
    )
    args = parser.parse_args()

    session_id = args.session_id or str(uuid.uuid4())

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"Input CSV not found: {csv_path}", file=sys.stderr)
        return 2

    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = HERE / "responses" / f"run-{ts}.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        rows = [
            {"query": (r.get("queries") or "").strip(), "step": (r.get("step") or "").strip()}
            for r in reader
        ]
    rows = [r for r in rows if r["query"]]
    if args.limit:
        rows = rows[: args.limit]

    print(f"Loaded {len(rows)} queries from {csv_path}")
    print(f"POSTing to {args.url}")
    print(f"Session ID (shared across all rows): {session_id}")
    print(f"Writing responses to {out_path}\n")

    with out_path.open("w", encoding="utf-8") as out:
        out.write(f"SESSION_ID: {session_id}\n\n")
        for index, row in enumerate(rows, start=1):
            query = row["query"]
            step = row["step"]
            payload = {"query": query, "step_number": step, "session_id": session_id}

            print(f"[{index}/{len(rows)}] {query!r} step={step}")
            t0 = time.monotonic()
            try:
                status, body = post_invoke(args.url, payload, args.timeout)
            except Exception as exc:
                status, body = 0, f"<request failed: {exc!r}>"
            elapsed = time.monotonic() - t0
            print(f"    -> status {status} in {elapsed:.2f}s")

            out.write(format_block(query, step, session_id, status, body, elapsed))
            out.write("\n")
            out.flush()

    print(f"\nDone. Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
