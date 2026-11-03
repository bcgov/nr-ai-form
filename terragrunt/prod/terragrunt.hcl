include {
  path = find_in_parent_folders()
}

inputs = {
  # Prod deploys to Azure Container Apps only
  deployment_type = "container_apps"

  # Keep at least one replica warm in prod to avoid cold starts (default is 0 / scale-to-zero)
  min_replicas = 1

  # Provision Azure AI Search and the Storage Account with Terraform in prod.
  # Their endpoint/keys/connection string are wired into the Container App from module
  # outputs, so AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_STORAGE_* and
  # AZURE_BLOBSTORAGE_CONNECTIONSTRING do not need to be set in the GitHub "prod" environment.
  # AZURE_SEARCH_INDEX_NAME is still required (the index is created by the indexing process).
  enable_search  = true
  enable_storage = true

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

  # Azure Document Intelligence is not provisioned in prod. Leave
  # AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT / AZURE_DOCUMENT_INTELLIGENCE_KEY unset in the
  # GitHub "prod" environment; the Container App secret is skipped when the key is empty.
}
