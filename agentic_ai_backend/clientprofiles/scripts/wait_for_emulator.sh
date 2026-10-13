#!/bin/sh
# Wait for Cosmos DB emulator to become ready before seeding.
# The emulator takes 20-40 seconds to start. We poll the root endpoint.

EMULATOR_URL="${COSMOS_EMULATOR_ENDPOINT:-https://azure-cosmos-emulator:8081}"
MAX_RETRIES=60
RETRY_INTERVAL=3

echo "Waiting for Cosmos emulator at ${EMULATOR_URL}..."

i=0
while [ $i -lt $MAX_RETRIES ]; do
    # -k skips TLS verification (emulator uses self-signed cert)
    if curl -sk "${EMULATOR_URL}/" > /dev/null 2>&1; then
        echo "Emulator is ready."
        exit 0
    fi
    i=$((i + 1))
    echo "  Attempt ${i}/${MAX_RETRIES} - not ready yet, retrying in ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

echo "ERROR: Emulator did not become ready after $((MAX_RETRIES * RETRY_INTERVAL)) seconds."
exit 1
