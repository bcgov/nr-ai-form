include {
  path = find_in_parent_folders()
}

inputs = {
  # Prod deploys to Azure Container Apps only
  deployment_type = "container_apps"

  # Keep at least one replica warm in prod to avoid cold starts (default is 0 / scale-to-zero)
  min_replicas = 1

  # Provision Azure AI Search and the Storage Account with Terraform in prod.
  # Their endpoint/keys are wired into the Container App from module outputs, so
  # AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY and AZURE_STORAGE_* do not need to be set in
  # the GitHub "prod" environment. The agents' AZURE_BLOBSTORAGE_CONNECTIONSTRING comes from the
  # "prod" environment SECRET of that name; if it is unset, the managed account's is used.
  # AZURE_SEARCH_INDEX_NAME is still required (the index is created by the indexing process).
  enable_search  = true
  enable_storage = true
  # The agents' blob container (AZURE_BLOBSTORAGE_CONTAINER, "assets" in prod) is set as a
  # variable in the GitHub "prod" environment, NOT here: the root terragrunt.hcl writes it into
  # terragrunt.auto.tfvars, which overrides anything in this inputs block. It is created manually
  # in the Terraform-managed Storage Account; the Terraform container ("agent-assets") is left as is.
  # With both enabled, Search also gets a shared private link to the Storage Account's blob
  # endpoint (approved during apply) and Storage Blob Data Reader for its managed identity, so
  # indexers can read containers with "ResourceId=<storage account id>;" and no account key.

  # Canada Central had insufficient Search capacity for standard x2 replicas (first prod
  # deploy failed with "insufficient capacity in region"). Start with 1 replica; raise to 2
  # (read SLA) in place once capacity allows - no recreate needed.
  search_replica_count = 1

  # Provision Azure OpenAI with a text-embedding-3-large deployment for the Search index /
  # knowledge base. Search reaches it over a shared private link (approved during apply) and
  # authenticates with its managed identity (Cognitive Services OpenAI User), so no key is needed.
  # Canada Central only offers GlobalStandard for this model (inference may run outside Canada).
  enable_openai = true

  # Provision Azure Managed Redis with Terraform in prod. Host, port and access key are
  # wired into the Container App from module outputs, so REDIS_HOST, REDIS_PORT,
  # REDIS_PASSWORD and REDIS_SSL do not need to be set in the GitHub "prod" environment.
  # REDIS_TTL_DAYS is optional (defaults to 14).
  enable_redis = true

  # Client profiles in Cosmos (AgentMemoryDB/ClientProfiles) are managed from Git: change
  # agentic_ai_backend/clientprofiles/prod/clientprofiles.json through a pull request, and the
  # next prod apply upserts it via the "<app_name>-cp-sync" Container Apps Job (infra/client_profiles.tf).
  # "id" and "clientId" are kept exactly as written and must be equal.
  # (These are not in the root terragrunt.auto.tfvars, so setting them here takes effect.)
  client_profiles_json        = file("${get_repo_root()}/agentic_ai_backend/clientprofiles/prod/clientprofiles.json")
  client_profiles_sync_script = file("${get_repo_root()}/agentic_ai_backend/clientprofiles/scripts/sync_client_profiles.py")

  # Front Door Premium reaches the Container App over Private Link (origin private_link + an
  # auto-approved private endpoint connection on the Container Apps environment). Azure requires
  # the environment's public network access to be Disabled for this, so it is disabled too: the
  # *.azurecontainerapps.io URL is no longer reachable from the internet - use Front Door.
  frontdoor_private_link_enabled = true

  # Azure Document Intelligence is not provisioned in prod. Leave
  # AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT / AZURE_DOCUMENT_INTELLIGENCE_KEY unset in the
  # GitHub "prod" environment; the Container App secret is skipped when the key is empty.
}
