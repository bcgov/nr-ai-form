"""Probe the configured tenant gateway using the shared evaluation transport."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.backend_client import BackendClient, BackendError  # noqa: E402


async def run(args: argparse.Namespace) -> int:
    try:
        client = BackendClient(
            base_url=args.url,
            timeout=args.idle_timeout,
            session_id=args.session_id,
            client_id=args.client_id,
            origin=args.origin,
            application_id=args.application_id,
        )
        try:
            response = await client.invoke(args.query, args.step_number)
            print(json.dumps(response, indent=2, ensure_ascii=False))
            return 0
        finally:
            await client.close()
    except (BackendError, ValueError) as exc:
        print(f"Gateway probe failed: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("BACKEND_API_URL") or os.getenv("BACKEND_WS_URL"))
    parser.add_argument("--origin", default=os.getenv("BACKEND_WS_ORIGIN"))
    parser.add_argument("--client-id", default=os.getenv("BACKEND_WS_CLIENT_ID"))
    parser.add_argument("--query", default="What is a water licence?")
    parser.add_argument("--step-number", default=os.getenv("BACKEND_WS_STEP", "step2-Eligibility"))
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--application-id", type=int, default=None)
    parser.add_argument("--idle-timeout", type=float, default=180.0)
    args = parser.parse_args()
    if args.url and not args.url.startswith(("ws://", "wss://")):
        parser.error("--url / BACKEND_API_URL must point to the gateway WebSocket /ws")
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
