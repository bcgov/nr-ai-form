"""Upsert client profiles into Azure Cosmos DB (AgentMemoryDB/ClientProfiles).

Used by the prod deploy: Terraform passes the reviewed JSON from
agentic_ai_backend/clientprofiles/prod/clientprofiles.json to the
"<app_name>-cp-sync" Container Apps Job, which runs this script inside the VNet
(Cosmos has public network access disabled) with its managed identity.

Rules:
  * The JSON is one profile object or a list of them.
  * Every profile the job receives has "id" and "clientId", and they are equal: the
    ClientProfiles container is partitioned on /id and the runtime does a point
    read with client_id as both id and partition key.
  * In the Git file, a profile may leave out both "id" and "clientId". Terraform
    (infra/client_profiles.tf) then generates one GUID, keeps it in state, and writes
    it into both fields before the job runs. Ids written in the file are kept as-is.
    This script never generates or rewrites ids itself.
  * Full process: agentic_ai_backend/clientprofiles/docs/azure-setup.md ("Prod Client Profiles")
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


PLACEHOLDER_ID = "00000000-0000-0000-0000-000000000000"


def parse_profiles(raw: str, allow_missing_ids: bool = False) -> list[dict[str, Any]]:
    """Parse and check profiles.

    allow_missing_ids=True is the source-file check (--validate-only): a profile may leave out
    both "id" and "clientId", because Terraform (infra/client_profiles.tf) generates one GUID and
    writes it into both before the sync job runs. The job itself always requires both.
    """
    data = json.loads(raw)
    profiles = data if isinstance(data, list) else [data]
    if not profiles or not all(isinstance(p, dict) for p in profiles):
        raise ValueError("Client profile JSON must be an object or a non-empty list of objects.")

    errors = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for index, profile in enumerate(profiles, start=1):
        item_id, client_id = profile.get("id"), profile.get("clientId")
        name = profile.get("clientName")
        label = client_id or item_id or name or f"profile #{index}"
        # Terraform keys the generated GUID on clientName, so it must be present and unique.
        if not name:
            errors.append(f"- {label}: 'clientName' is required")
        elif name in seen_names:
            errors.append(f"- {label}: duplicate clientName '{name}'")
        seen_names.add(name)

        if allow_missing_ids and not item_id and not client_id:
            continue  # Terraform will generate the id.
        if not item_id or not client_id:
            errors.append(f"- {label}: both 'id' and 'clientId' are required")
        elif item_id != client_id:
            errors.append(f"- {label}: 'id' ({item_id}) must equal 'clientId' ({client_id})")
        elif item_id in seen_ids:
            errors.append(f"- {label}: duplicate id")
        seen_ids.add(item_id)
    if errors:
        raise ValueError("Client profile id check failed:\n" + "\n".join(errors))

    # The model requires clientId; use a placeholder for profiles whose id Terraform will generate.
    validate_client_profiles(
        [p if p.get("clientId") else {**p, "clientId": PLACEHOLDER_ID} for p in profiles]
    )
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
                profiles = parse_profiles(f.read(), allow_missing_ids=True)
            labels = [p.get("id") or f"{p['clientName']} (id generated by Terraform)" for p in profiles]
            print(f"OK: {len(profiles)} profile(s) valid: {', '.join(labels)}")
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
