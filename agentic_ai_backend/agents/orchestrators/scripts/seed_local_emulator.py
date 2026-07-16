
"""Seed the local Cosmos DB emulator with client profile data.

Prerequisites:
    1. Start the emulator: docker-compose up azure-cosmos-emulator
    2. Wait for it to be ready
    3. Install SDK: pip install azure-cosmos

Run from the orchestrators directory:
    cd agentic_ai_backend/agents/orchestrators
    .venv\\Scripts\\python scripts/seed_local_emulator.py
"""

import json
import os
import sys
import uuid

from azure.cosmos import CosmosClient, PartitionKey
from clientprofiles import TenantSettingsValidationError, validate_client_profiles


BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


ENDPOINT = os.getenv("COSMOS_EMULATOR_ENDPOINT", "https://localhost:8081")
# The default primary key for the Azure Cosmos DB Emulator is a well-known key used across all local installations.
KEY = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
DATABASE_NAME = "AgentMemoryDB"
CONTAINER_NAME = "ClientProfiles"
SEED_FILE = os.getenv(
    "SEED_FILE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "clientprofiles", "seed", "client_profiles.json"),
)


def load_profiles(seed_path: str) -> list[dict]:
    print(f"\nLoading profiles from: {seed_path}")
    with open(seed_path, encoding="utf-8") as f:
        profiles = json.load(f)

    for profile in profiles:
        # Keep local seeding convenient, but validate the generated id with the rest of the profile.
        if "clientId" not in profile:
            profile["clientId"] = str(uuid.uuid4())
        profile["id"] = profile["clientId"]

    print("Validating tenant profiles before upsert...")
    validate_client_profiles(profiles)
    print(f"Validation passed for {len(profiles)} tenant profile(s).")
    return profiles


def seed() -> None:
    seed_path = os.path.normpath(SEED_FILE)

    print(f"Target:    {ENDPOINT} (local emulator)")
    print(f"Database:  {DATABASE_NAME}")
    print(f"Container: {CONTAINER_NAME}")
    print(f"Seed file: {seed_path}")

    profiles = load_profiles(seed_path)

    # TLS is disabled because the emulator uses a self-signed certificate.
    # Endpoint discovery is disabled because the Docker emulator can advertise
    # its internal container IP, which is not reachable from host-run scripts.
    client = CosmosClient(
        ENDPOINT,
        credential=KEY,
        connection_verify=False,
        enable_endpoint_discovery=False,
    )

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
    except TenantSettingsValidationError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        print(
            "\nMake sure the Cosmos emulator is running:\n"
            "    docker-compose up azure-cosmos-emulator",
            file=sys.stderr,
        )
        sys.exit(1)