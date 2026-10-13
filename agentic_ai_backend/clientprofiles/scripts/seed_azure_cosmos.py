"""Seed an Azure Cosmos DB account with client profile data.

Prerequisites:
    1. Create the Cosmos DB account in Azure Portal (NoSQL API)
    2. Get the endpoint URL and primary key from Azure Portal > Keys
    3. Install SDK: pip install azure-cosmos

Run from agentic_ai_backend:
    python clientprofiles/scripts/seed_azure_cosmos.py
"""

import base64
import json
import os
import sys
import uuid

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from azure.cosmos import CosmosClient, PartitionKey
from clientprofiles import validate_client_profiles


ENDPOINT = "<Endpoint>"
KEY = "<your azure cosmos db key>"
DATABASE_NAME = "AgentMemoryDB"
CONTAINER_NAME = "ClientProfiles"
SEED_FILE = os.path.join(os.path.dirname(__file__), "..", "seed", "client_profiles.json")


def validate_cosmos_key() -> None:
    if "<" in ENDPOINT or "<" in KEY:
        raise RuntimeError(
            "Please update ENDPOINT and KEY at the top of this script with your Azure Cosmos DB account details."
        )

    try:
        decoded = base64.b64decode(KEY)
        print(f"Key validation: OK ({len(decoded)} bytes decoded)")
    except Exception as exc:
        raise RuntimeError(
            "KEY is not valid base64. Re-copy the PRIMARY KEY from Azure Portal using the copy button."
        ) from exc


def load_profiles(seed_path: str) -> list[dict]:
    print(f"\nLoading profiles from: {seed_path}")
    with open(seed_path, encoding="utf-8") as f:
        profiles = json.load(f)

    for profile in profiles:
        if "clientId" not in profile:
            profile["clientId"] = str(uuid.uuid4())
        profile["id"] = profile["clientId"]

    print("Validating tenant profiles before upsert...")
    validate_client_profiles(profiles)
    print(f"Validation passed for {len(profiles)} tenant profile(s).")
    return profiles


def seed() -> None:
    validate_cosmos_key()
    seed_path = os.path.normpath(SEED_FILE)

    print(f"Target:    {ENDPOINT} (Azure Cosmos DB)")
    print(f"Database:  {DATABASE_NAME}")
    print(f"Container: {CONTAINER_NAME}")
    print(f"Seed file: {seed_path}")

    profiles = load_profiles(seed_path)

    client = CosmosClient(ENDPOINT, credential=KEY)

    print(f"Creating database '{DATABASE_NAME}' if not exists...")
    db = client.create_database_if_not_exists(DATABASE_NAME)

    print(f"Creating container '{CONTAINER_NAME}' (partition key: /clientId) if not exists...")
    container = db.create_container_if_not_exists(
        id=CONTAINER_NAME,
        partition_key=PartitionKey(path="/clientId"),
    )

    for profile in profiles:
        container.upsert_item(profile)
        print(f"  Done: {profile['clientId']} - {profile['clientName']}")

    print(f"\nDone. {len(profiles)} profiles upserted into {DATABASE_NAME}/{CONTAINER_NAME}.")


if __name__ == "__main__":
    try:
        seed()
    except FileNotFoundError as exc:
        print(f"\nError: Seed file not found: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)