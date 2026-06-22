"""Quick test script to verify the client profile store works end-to-end.

Tests resolve() with a real client_id against the Cosmos DB (emulator or Azure).
Make sure your .env has the correct AZURE_COSMOS_* variables set.

Run from the orchestrators directory:
    cd agentic_ai_backend/agents/orchestrators
    .venv/Scripts/python scripts/test_resolve.py
"""

import asyncio
import sys
import os

# Load .env so the factory picks up the Cosmos connection settings
from dotenv import load_dotenv
load_dotenv()

# Add parent dir to path so clientprofiles package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from clientprofiles import get_client_profile_store, ClientIdRequiredError, ClientProfileNotFoundError


async def main():
    print("=" * 60)
    print("Client Profile Store - resolve() test")
    print("=" * 60)

    store = get_client_profile_store()
    print(f"\nStore created: {type(store).__name__}")

    # Test 1: resolve with a known client_id
    test_client_id = "11111111-1111-4111-8111-111111111111"
    print(f"\n--- Test 1: resolve('{test_client_id}') ---")
    try:
        profile = await store.resolve(test_client_id)
        print(f"  SUCCESS: Found profile")
        print(f"  clientId:   {profile.clientId}")
        print(f"  clientName: {profile.clientName}")
        print(f"  corsOrigins: {profile.corsOrigins}")
        print(f"  subAgents:  {len(profile.subAgents)} agents")
        for agent in profile.subAgents:
            print(f"    - {agent.agentType} (enabled={agent.enabled})")
        if profile.tenantResources:
            print(f"  tenantResources:")
            print(f"    blobStorageConnection: {'(set)' if profile.tenantResources.blobStorageConnectionString else '(not set)'}")
            print(f"    blobContainer: {profile.tenantResources.blobContainerName}")
            print(f"    promptBasePath: {profile.tenantResources.promptBasePath}")
            print(f"    formDefBasePath: {profile.tenantResources.formDefinitionBasePath}")
        if profile.orchestratorPrompts:
            print(f"  orchestratorPrompts:")
            print(f"    dispatcherPath: {profile.orchestratorPrompts.dispatcherPromptPath}")
            print(f"    aggregatorPath: {profile.orchestratorPrompts.aggregatorPromptPath}")
        print(f"\n  --- Full model dump (JSON) ---")
        print(f"  {profile.model_dump_json(indent=2)}")
    except ClientProfileNotFoundError as e:
        print(f"  NOT FOUND: {e}")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")

    # Test 2: resolve with None (should raise ClientIdRequiredError)
    print(f"\n--- Test 2: resolve(None) ---")
    try:
        await store.resolve(None)
        print(f"  UNEXPECTED: Should have raised ClientIdRequiredError")
    except ClientIdRequiredError as e:
        print(f"  CORRECT: Raised ClientIdRequiredError - {e}")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")

    # Test 3: resolve with a non-existent client_id
    fake_id = "99999999-9999-4999-8999-999999999999"
    print(f"\n--- Test 3: resolve('{fake_id}') ---")
    try:
        await store.resolve(fake_id)
        print(f"  UNEXPECTED: Should have raised ClientProfileNotFoundError")
    except ClientProfileNotFoundError as e:
        print(f"  CORRECT: Raised ClientProfileNotFoundError - {e}")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())



























































































