output "openai_account_id" {
  description = "The ID of the Azure OpenAI account."
  value       = azurerm_cognitive_account.main.id
}

output "openai_account_name" {
  description = "The name of the Azure OpenAI account."
  value       = azurerm_cognitive_account.main.name
}

output "openai_endpoint" {
  description = "The endpoint of the Azure OpenAI account (use as resourceUri in the Search vectorizer)."
  value       = azurerm_cognitive_account.main.endpoint
}

output "embedding_deployment_name" {
  description = "The name of the text-embedding-3-large deployment."
  value       = azurerm_cognitive_deployment.embedding.name
}
