"""Send one question N times to the running ConversationAgent and report whether chunk order changes.

Talks to the agent already running in docker (http://localhost:8000/invoke), so
Azure Search traffic goes through the container's privoxy setup. Chunk ids are
read from the container's "Azure AI Search retrieval:" log lines after each call.
Standard library only:

    python scripts/chunk_order_check.py "your question" --runs 20
    python scripts/chunk_order_check.py "your question" --global-stats --session-id test-1

In llm mode the LLM writes the search query, so the query actually sent is
reported alongside each ordering. Client settings default to the water tenant's
conversationAgent block in clientprofiles/seed/client_profiles.json.
"""
import argparse
import json
import os
import subprocess
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILES = os.path.join(HERE, "..", "..", "..", "clientprofiles", "seed", "client_profiles.json")
WATER_CLIENT_ID = "11111111-1111-4111-8111-111111111111"
RETRIEVAL_PREFIX = "Azure AI Search retrieval: "


def load_client_settings(path: str | None) -> dict:
    if path:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    with open(DEFAULT_PROFILES, encoding="utf-8") as f:
        profiles = json.load(f)
    profile = next(p for p in profiles if p["clientId"] == WATER_CLIENT_ID)
    settings = next(a for a in profile["subAgents"] if a["agentType"] == "conversationAgent")
    settings.setdefault("clientId", WATER_CLIENT_ID)
    # The orchestrator normally fills this in; it only keys the instructions cache.
    settings.setdefault("configFingerprint", "chunk-order-check")
    return settings


def container_log_lines(container: str) -> list[str]:
    result = subprocess.run(
        ["docker", "logs", container],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    # Retrieval lines are print()ed to stdout; uvicorn access logs go to stderr.
    return result.stdout.splitlines()


def invoke(url: str, query: str, session_id: str | None, client_settings: dict, timeout: int) -> str:
    body = json.dumps({"query": query, "session_id": session_id, "client_settings": client_settings}).encode("utf-8")
    request = urllib.request.Request(f"{url.rstrip('/')}/invoke", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read()).get("response", "")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"/invoke returned {e.code}: {e.read().decode('utf-8', errors='replace')}") from e


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--container", default="agentic_ai_backend-conversation-agent-1")
    parser.add_argument("--client-settings", help="JSON file with a conversationAgent block ({'config': {...}})")
    parser.add_argument("--global-stats", action="store_true", help='send scoringStatistics: "global"')
    parser.add_argument("--session-id", help="send this sessionId on every search request")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--out", default="chunk_order_results.json")
    args = parser.parse_args()

    client_settings = load_client_settings(args.client_settings)
    config = client_settings.setdefault("config", {})
    if args.global_stats:
        config["azureSearchScoringStatisticsGlobal"] = True
    if args.session_id:
        config["azureSearchUseSessionId"] = True

    runs = []
    for i in range(1, args.runs + 1):
        seen = len(container_log_lines(args.container))
        response = invoke(args.url, args.query, args.session_id, client_settings, args.timeout)
        new_lines = container_log_lines(args.container)[seen:]
        searches = [json.loads(line[len(RETRIEVAL_PREFIX):]) for line in new_lines if line.startswith(RETRIEVAL_PREFIX)]
        runs.append({"response": response, "searches": searches})
        print(f"run {i}/{args.runs}: {len(searches)} search call(s)")

    # Compare the first search call of each run - that is the one built from the question.
    firsts = [r["searches"][0] for r in runs if r["searches"]]
    orderings = Counter(tuple(c["id"] for c in s["chunks"]) for s in firsts if not s["error"])
    queries = Counter(s["query"] for s in firsts)
    ranks: dict[str, list[int]] = {}
    for s in firsts:
        for rank, chunk in enumerate(s["chunks"], start=1):
            ranks.setdefault(chunk["id"], []).append(rank)

    errors = sum(1 for s in firsts if s["error"])
    print(f"\nQuestion: {args.query!r}  runs: {args.runs}  with search: {len(firsts)}  errors: {errors}")
    print(f"\nDistinct search queries written by the LLM: {len(queries)}")
    for query, count in queries.most_common():
        print(f"  {count}/{len(firsts)}  {query!r}")
    print(f"\nDistinct chunk orderings: {len(orderings)}")
    for i, (order, count) in enumerate(orderings.most_common(), start=1):
        print(f"  ordering {i}: {count}/{len(firsts)}  {list(order)}")
    print(f"\n  {'chunk id':<60} {'seen':>6} {'avg rank':>9} {'ranks':>8}")
    for chunk_id, chunk_ranks in sorted(ranks.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
        print(f"  {str(chunk_id):<60} {len(chunk_ranks):>3}/{len(firsts):<2} {sum(chunk_ranks) / len(chunk_ranks):>9.2f} "
              f"{min(chunk_ranks)}-{max(chunk_ranks):<6}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"question": args.query, "config": config, "runs": runs}, f, indent=2)
    print(f"\nRaw results written to {args.out}")


if __name__ == "__main__":
    main()
