"""Seed a Azure Cosmos DB account with client profile data.

Prerequisites:
    1. Create the Cosmos DB account in Azure Portal (NoSQL API)
    2. Get the endpoint URL and primary key from Azure Portal > Keys
    3. Install SDK: pip install azure-cosmos

Run from the orchestrators directory:
    cd agentic_ai_backend/agents/orchestrators
    .venv/Scripts/python scripts/seed_azure_cosmos.py
"""

import json
import os
import sys

from azure.cosmos import CosmosClient, PartitionKey


# ==============================================================================
# CONFIGURATION - UPDATE THESE VALUES before running
# ==============================================================================

# Your Azure Cosmos DB endpoint (from Azure Portal > Cosmos DB account > Keys)
ENDPOINT = "<Endpoint>"  # e.g. "https://your-account.documents.azure.com:443/"

# Your Azure Cosmos DB primary key (from Azure Portal > Cosmos DB account > Keys)
KEY = "<your azure cosmos db key>"

# Database and container names
DATABASE_NAME = "AgentMemoryDB"
CONTAINER_NAME = "ClientProfiles"

# Path to the seed JSON file (relative to this script)
SEED_FILE = os.path.join(
    os.path.dirname(__file__), "..", "clientprofiles", "seed", "client_profiles.json"
)

# ==============================================================================
# SCRIPT - no changes needed below this line
# ==============================================================================


def seed():
    if "<YOUR_" in ENDPOINT or "<YOUR_" in KEY:
        print(
            "ERROR: Please update ENDPOINT and KEY at the top of this script\n"
            "       with your Azure Cosmos DB account details.\n"
            "       (Azure Portal > Cosmos DB account > Keys)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate the key is valid base64 before connecting
    import base64
    try:
        decoded = base64.b64decode(KEY)
        print(f"Key validation: OK ({len(decoded)} bytes decoded)")
    except Exception as e:
        print(f"ERROR: KEY is not valid base64: {e}", file=sys.stderr)
        print(f"       Key length: {len(KEY)} characters", file=sys.stderr)
        print(f"       Key ends with: ...{KEY[-10:]}", file=sys.stderr)
        print(f"       Expected: 88 characters ending with '=='", file=sys.stderr)
        print(f"\n       Re-copy the PRIMARY KEY from Azure Portal using the copy button.", file=sys.stderr)
        sys.exit(1)

    seed_path = os.path.normpath(SEED_FILE)

    print(f"Target:    {ENDPOINT} (Azure Cosmos DB)")
    print(f"Database:  {DATABASE_NAME}")
    print(f"Container: {CONTAINER_NAME}")
    print(f"Seed file: {seed_path}")
    print()

    # TLS enabled for real Azure (not the emulator)
    client = CosmosClient(ENDPOINT, credential=KEY)

    print(f"Creating database '{DATABASE_NAME}' if not exists...")
    db = client.create_database_if_not_exists(DATABASE_NAME)

    print(f"Creating container '{CONTAINER_NAME}' (partition key: /clientId) if not exists...")
    container = db.create_container_if_not_exists(
        id=CONTAINER_NAME,
        partition_key=PartitionKey(path="/clientId"),
    )

    print(f"\nLoading profiles from: {seed_path}")
    with open(seed_path, encoding="utf-8") as f:
        profiles = json.load(f)

    for profile in profiles:
        container.upsert_item(profile)
        print(f"  Done: {profile['clientId']} - {profile['clientName']}")

    print(f"\nDone. {len(profiles)} profiles upserted into {DATABASE_NAME}/{CONTAINER_NAME}.")


if __name__ == "__main__":
    try:
        seed()
    except FileNotFoundError as e:
        print(f"\nError: Seed file not found: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        raise
