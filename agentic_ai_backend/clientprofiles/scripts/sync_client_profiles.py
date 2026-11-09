"""Upsert client profiles into Azure Cosmos DB (AgentMemoryDB/ClientProfiles).

Used by the prod deploy: Terraform passes the reviewed JSON from
agentic_ai_backend/clientprofiles/prod/clientprofiles.json to the
"<app_name>-cp-sync" Container Apps Job, which runs this script inside the VNet
(Cosmos has public network access disabled) with its managed identity.

Rules:
  * The JSON is one profile object or a list of them.
  * Every profile must have "id" and "clientId", and they must be equal: the
    ClientProfiles container is partitioned on /id and the runtime does a point
    read with client_id as both id and partition key.
  * Items are upserted as-is (id/clientId are never generated or rewritten).
  * Items that are not in the JSON are left untouched (no deletes).

Environment:
  CLIENT_PROFILES_JSON           the profile JSON (required)
  AZURE_COSMOS_DB_ENDPOINT       Cosmos account endpoint (required)
  AZURE_COSMOS_DB_DATABASE_NAME  default AgentMemoryDB
  AZURE_COSMOS_DB_CONTAINER_NAME default ClientProfiles
  AZURE_COSMOS_DB_KEY            optional; managed identity is used when unset

Local check (no Cosmos access):
  python clientprofiles/scripts/sync_client_profiles.py --validate-only clientprofiles/prod/clientprofiles.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.isdir(os.path.join(BACKEND_ROOT, "clientprofiles")) and BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from clientprofiles import validate_client_profiles  # noqa: E402

# Cosmos data-plane RBAC for a new managed identity can take a few minutes to apply.
MAX_ATTEMPTS = 10
RETRY_SECONDS = 30


def parse_profiles(raw: str) -> list[dict[str, Any]]:
    data = json.loads(raw)
    profiles = data if isinstance(data, list) else [data]
    if not profiles or not all(isinstance(p, dict) for p in profiles):
        raise ValueError("Client profile JSON must be an object or a non-empty list of objects.")

    errors = []
    seen: set[str] = set()
    for index, profile in enumerate(profiles, start=1):
        item_id, client_id = profile.get("id"), profile.get("clientId")
        label = client_id or item_id or f"profile #{index}"
        if not item_id or not client_id:
            errors.append(f"- {label}: both 'id' and 'clientId' are required")
        elif item_id != client_id:
            errors.append(f"- {label}: 'id' ({item_id}) must equal 'clientId' ({client_id})")
        elif item_id in seen:
            errors.append(f"- {label}: duplicate id")
        seen.add(item_id)
    if errors:
        raise ValueError("Client profile id check failed:\n" + "\n".join(errors))

    validate_client_profiles(profiles)
    return profiles


def upsert(profiles: list[dict[str, Any]]) -> None:
    from azure.cosmos import CosmosClient
    from azure.cosmos.exceptions import CosmosHttpResponseError

    endpoint = os.environ["AZURE_COSMOS_DB_ENDPOINT"]
    database_name = os.getenv("AZURE_COSMOS_DB_DATABASE_NAME", "AgentMemoryDB")
    container_name = os.getenv("AZURE_COSMOS_DB_CONTAINER_NAME", "ClientProfiles")
    key = os.getenv("AZURE_COSMOS_DB_KEY")
    if key:
        credential: Any = key
    else:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()

    print(f"Target: {endpoint} {database_name}/{container_name} ({'key' if key else 'managed identity'})")
    container = (
        CosmosClient(endpoint, credential=credential)
        .get_database_client(database_name)
        .get_container_client(container_name)
    )

    for profile in profiles:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                container.upsert_item(profile)
                break
            except CosmosHttpResponseError as exc:
                if exc.status_code != 403 or attempt == MAX_ATTEMPTS:
                    raise
                print(f"  403 (RBAC not applied yet?), retry {attempt}/{MAX_ATTEMPTS - 1} in {RETRY_SECONDS}s")
                time.sleep(RETRY_SECONDS)
        print(f"  upserted {profile['id']} - {profile.get('clientName', '')}")

    print(f"Done. {len(profiles)} profile(s) upserted.")


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 3 and argv[1] == "--validate-only":
            with open(argv[2], encoding="utf-8") as f:
                profiles = parse_profiles(f.read())
            print(f"OK: {len(profiles)} profile(s) valid: {', '.join(p['id'] for p in profiles)}")
            return 0

        raw = os.getenv("CLIENT_PROFILES_JSON")
        if not raw:
            raise ValueError("CLIENT_PROFILES_JSON is not set.")
        upsert(parse_profiles(raw))
        return 0
    except Exception as exc:  # noqa: BLE001 - surface any failure as a non-zero job exit
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
