"""Smoke test for the API Backend WebSocket gateway.

Endpoint and origin are read from the environment (see evaluation/.env.example):
    BACKEND_WS_URL      wss://<host>/ws
    BACKEND_WS_ORIGIN   https://<allowed-origin>

Usage:
    python evaluation/tools/ws_smoke_test.py --query "..."
    python evaluation/tools/ws_smoke_test.py --url wss://<host>/ws --origin https://<origin>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from pathlib import Path

import websockets
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DEFAULT_URL = os.getenv("BACKEND_WS_URL", "")
DEFAULT_ORIGIN = os.getenv("BACKEND_WS_ORIGIN", "")


async def run(url: str, origin: str, payload: dict, idle_timeout: float) -> int:
    print(f"-> connecting: {url}")
    print(f"-> origin:     {origin}")
    started = time.perf_counter()
    try:
        async with websockets.connect(
            url,
            origin=origin,
            open_timeout=30,
            close_timeout=10,
            max_size=None,
        ) as ws:
            print(f"<- connected in {time.perf_counter() - started:.2f}s "
                  f"(subprotocol={ws.subprotocol})")
            print(f"-> send: {json.dumps(payload)}")
            await ws.send(json.dumps(payload))

            frames = 0
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=idle_timeout)
                except asyncio.TimeoutError:
                    print(f"<- idle {idle_timeout}s with no further frames; stopping")
                    break
                except websockets.ConnectionClosed as exc:
                    print(f"<- closed by server: code={exc.code} reason={exc.reason!r}")
                    break

                frames += 1
                elapsed = time.perf_counter() - started
                try:
                    parsed = json.loads(raw)
                    pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                except (TypeError, ValueError):
                    pretty = raw if isinstance(raw, str) else repr(raw)
                print(f"\n<- frame #{frames} @ {elapsed:.2f}s\n{pretty}")

            print(f"\nTotal frames: {frames} in {time.perf_counter() - started:.2f}s")
            return 0 if frames else 1
    except Exception as exc:  # connection-level failure
        print(f"!! {type(exc).__name__}: {exc}")
        return 2


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--origin", default=DEFAULT_ORIGIN)
    p.add_argument("--client-id", default="11111111-1111-4111-8111-111111111111")
    p.add_argument("--query", default="What is a water licence?")
    p.add_argument("--step-number", default="step2-Eligibility")
    p.add_argument("--session-id", default=f"smoke-{uuid.uuid4().hex[:8]}")
    p.add_argument("--application-id", type=int, default=234554)
    p.add_argument("--idle-timeout", type=float, default=90.0)
    args = p.parse_args()

    if not args.url:
        p.error("no endpoint: set BACKEND_WS_URL in evaluation/.env or pass --url")

    payload = {
        "client_id": args.client_id,
        "query": args.query,
        "step_number": args.step_number,
        "session_id": args.session_id,
        "application_id": args.application_id,
    }
    return asyncio.run(run(args.url, args.origin, payload, args.idle_timeout))


if __name__ == "__main__":
    raise SystemExit(main())
