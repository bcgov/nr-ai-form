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

  # Azure Document Intelligence is not provisioned in prod. Leave
  # AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT / AZURE_DOCUMENT_INTELLIGENCE_KEY unset in the
  # GitHub "prod" environment; the Container App secret is skipped when the key is empty.
}
