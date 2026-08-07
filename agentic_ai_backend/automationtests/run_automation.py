"""
Automation runner for the orchestrator /ws WebSocket endpoint.

Reads a CSV of (queries, step) rows, sends each row as a JSON message over a
single WebSocket connection to the orchestrator, sharing one session UUID
across the whole run (so the orchestrator's multi-turn memory threads them as
one conversation), and writes every response to a timestamped .txt file
under `responses/`. Each block is separated by a line of `=`.

Usage:
    python run_automation.py
    python run_automation.py --csv testscripts1.csv --output my_run.txt
    python run_automation.py --url ws://localhost:8002/ws --timeout 60
    python run_automation.py --limit 3                       # first 3 rows only
    python run_automation.py --session-id 1234-...           # reuse a specific session
    python run_automation.py --client-id 11111111-1111-4111-8111-111111111111
"""

import argparse
import asyncio
import csv
import datetime
import json
import sys
import time
import uuid
from pathlib import Path

import websockets


SEPARATOR = "=" * 80
DEFAULT_URL = "ws://localhost:8002/ws"
DEFAULT_CLIENT_ID = "11111111-1111-4111-8111-111111111111"  # "Water Permit App" seed profile
HERE = Path(__file__).parent


async def send_invoke(
    websocket,
    client_id: str,
    query: str,
    step: str,
    session_id: str,
    timeout: float,
) -> str:
    payload = {
        "client_id": client_id,
        "query": query,
        "step_number": step,
        "session_id": session_id,
    }
    await websocket.send(json.dumps(payload))
    return await asyncio.wait_for(websocket.recv(), timeout=timeout)


def format_block(
    query: str,
    step: str,
    session_id: str,
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
        f"ELAPSED:    {elapsed:.2f}s\n"
        f"{SEPARATOR}\n"
        f"{pretty}\n"
    )


async def run(args) -> int:
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
    print(f"Connecting to {args.url}")
    print(f"Client ID: {args.client_id}")
    print(f"Session ID (shared across all rows): {session_id}")
    print(f"Writing responses to {out_path}\n")

    with out_path.open("w", encoding="utf-8") as out:
        out.write(f"SESSION_ID: {session_id}\n\n")
        async with websockets.connect(args.url, open_timeout=args.timeout) as websocket:
            for index, row in enumerate(rows, start=1):
                query = row["query"]
                step = row["step"]

                print(f"[{index}/{len(rows)}] {query!r} step={step}")
                t0 = time.monotonic()
                try:
                    body = await send_invoke(
                        websocket, args.client_id, query, step, session_id, args.timeout
                    )
                except Exception as exc:
                    body = f"<request failed: {exc!r}>"
                elapsed = time.monotonic() - t0
                print(f"    -> received in {elapsed:.2f}s")

                out.write(format_block(query, step, session_id, body, elapsed))
                out.write("\n")
                out.flush()

    print(f"\nDone. Wrote {out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        default=str(HERE / "testscripts2-edgecases.csv"),
        help="Input CSV with `queries` and `step` columns.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Orchestrator WebSocket URL.")
    parser.add_argument(
        "--client-id",
        default=DEFAULT_CLIENT_ID,
        help="Tenant client_id required by the /ws route (see clientprofiles/seed/client_profiles.json).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output .txt path. Defaults to responses/run-<timestamp>.txt next to this script.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Timeout per request in seconds.",
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
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
