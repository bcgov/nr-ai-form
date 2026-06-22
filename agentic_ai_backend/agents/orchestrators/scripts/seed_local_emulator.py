"""Seed the LOCAL Cosmos DB emulator with client profile data.

Prerequisites:
    1. Start the emulator:  docker-compose up azure-cosmos-emulator
    2. Wait ~30 seconds for it to be ready
    3. Install SDK:  pip install azure-cosmos

Run from the orchestrators directory:
    cd agentic_ai_backend/agents/orchestrators
    .venv\Scripts\python scripts/seed_local_emulator.py
"""

import json
import os
import sys

from azure.cosmos import CosmosClient, PartitionKey

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  CONFIGURATION — update these if your local setup differs                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Cosmos emulator endpoint (default: https://localhost:8081)
ENDPOINT = "https://localhost:8081"

# Well-known emulator master key (public, not a secret)
KEY = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="

# Database and container names
DATABASE_NAME = "AgentMemoryDB"
CONTAINER_NAME = "ClientProfiles"

# Path to the seed JSON file (relative to this script's directory)
SEED_FILE = os.path.join(
    os.path.dirname(__file__), "..", "clientprofiles", "seed", "client_profiles.json"
)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SCRIPT — no changes needed below this line                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


def seed() -> None:
    seed_path = os.path.normpath(SEED_FILE)

    print(f"Target:    {ENDPOINT} (local emulator)")
    print(f"Database:  {DATABASE_NAME}")
    print(f"Container: {CONTAINER_NAME}")
    print(f"Seed file: {seed_path}")
    print()

    # TLS disabled — emulator uses a self-signed certificate
    client = CosmosClient(ENDPOINT, credential=KEY, connection_verify=False)

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
        print(f"  ✓ {profile['clientId']} — {profile['clientName']}")

    print(f"\nDone. {len(profiles)} profiles upserted into {DATABASE_NAME}/{CONTAINER_NAME}.")


if __name__ == "__main__":
    try:
        seed()
    except FileNotFoundError as e:
        print(f"\nError: Seed file not found: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        print(
            "\nMake sure the Cosmos emulator is running:\n"
            "    docker-compose up azure-cosmos-emulator",
            file=sys.stderr,
        )
        sys.exit(1)
