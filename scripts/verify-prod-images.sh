#!/bin/bash

# Verify that the images promoted to prod are byte-for-byte the same as the tested images.
# Compares manifest digests (not tag names) in GHCR, and optionally what the prod
# Container Apps are actually configured to run.
#
# Usage:
#   ./scripts/verify-prod-images.sh <test_tag> [prod_tag] [resource_group]
#
#   test_tag        Tag that was promoted, e.g. test-aca-42
#   prod_tag        Tag created by "Deploy ACA to Prod", e.g. prod-aca-7 (default: prod)
#   resource_group  Prod resource group; when set, also checks the running Container Apps
#
# Prereqs: docker with buildx, logged in to ghcr.io (docker login ghcr.io, PAT with read:packages);
#          az CLI logged in to the prod subscription when resource_group is given.

set -euo pipefail

# On Windows (Git Bash), az.cmd emits CRLF output; strip the trailing '\r'.
az() { command az "$@" | tr -d '\r'; }

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

IMAGE_PREFIX="${IMAGE_PREFIX:-ghcr.io/bcgov/nr-ai-form}"
IMAGES="orchestrator_agent conversation_agent formsupport_agent api_backend"

TEST_TAG="${1:-}"
PROD_TAG="${2:-prod}"
RESOURCE_GROUP="${3:-}"

if [[ -z "$TEST_TAG" ]]; then
  echo "Usage: $0 <test_tag> [prod_tag] [resource_group]"
  exit 2
fi

# Prints the manifest digest of an image reference (tag or @sha256), empty if not found.
# Some buildx versions ignore '{{.Manifest.Digest}}', so read the first "digest" from the JSON
# (the top-level one; the per-platform digests come after it).
digest_of() {
  docker buildx imagetools inspect "$1" --format '{{json .Manifest}}' 2>/dev/null \
    | tr -d '\r' | grep -m1 -o '"digest": *"sha256:[0-9a-f]*"' | grep -o 'sha256:[0-9a-f]*' || true
}

failed=0
declare -A TEST_DIGEST

echo -e "${YELLOW}== GHCR: $TEST_TAG vs $PROD_TAG ==${NC}"
for img in $IMAGES; do
  t=$(digest_of "$IMAGE_PREFIX/$img:$TEST_TAG")
  p=$(digest_of "$IMAGE_PREFIX/$img:$PROD_TAG")
  TEST_DIGEST[$img]="$t"
  if [[ -z "$t" || -z "$p" ]]; then
    echo -e "${RED}MISSING ${NC} $img  test=${t:-<not found>}  prod=${p:-<not found>}"
    failed=1
  elif [[ "$t" == "$p" ]]; then
    echo -e "${GREEN}SAME    ${NC} $img  $t"
  else
    echo -e "${RED}DIFFERENT${NC} $img  test=$t  prod=$p"
    failed=1
  fi
done

if [[ -n "$RESOURCE_GROUP" ]]; then
  echo
  echo -e "${YELLOW}== Container Apps in $RESOURCE_GROUP ==${NC}"
  for app in $(az containerapp list -g "$RESOURCE_GROUP" --query "[].name" -o tsv); do
    revision=$(az containerapp show -g "$RESOURCE_GROUP" -n "$app" --query properties.latestReadyRevisionName -o tsv)
    for ref in $(az containerapp show -g "$RESOURCE_GROUP" -n "$app" --query "properties.template.containers[].image" -o tsv); do
      # Image name without registry path and tag/digest, e.g. orchestrator_agent
      name="${ref##*/}"; name="${name%%@*}"; name="${name%%:*}"
      expected="${TEST_DIGEST[$name]:-}"
      if [[ -z "$expected" ]]; then
        echo -e "${YELLOW}SKIP    ${NC} $app  $ref (not a promoted image)"
        continue
      fi
      running=$(digest_of "$ref")
      if [[ "$running" == "$expected" ]]; then
        echo -e "${GREEN}SAME    ${NC} $app  $ref  $running  revision=$revision"
      else
        echo -e "${RED}DIFFERENT${NC} $app  $ref  running=${running:-<not found>}  test=$expected  revision=$revision"
        failed=1
      fi
    done
  done
fi

echo
if [[ $failed -eq 0 ]]; then
  echo -e "${GREEN}Prod images match $TEST_TAG.${NC}"
else
  echo -e "${RED}Prod images do NOT match $TEST_TAG.${NC}"
fi
exit $failed
