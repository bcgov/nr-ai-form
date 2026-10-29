# Creates the GitHub "prod" environment (if missing) and adds the secret/variable
# NAMES the ACA deploy needs, with placeholder values. Existing entries are skipped,
# so real values are never overwritten.
#
# Usage:  .\seed-prod-env.ps1            # dry run, shows what would be created
#         .\seed-prod-env.ps1 -Apply     # actually creates them
param(
    [switch]$Apply,
    [string]$Repo = "bcgov/nr-ai-form",
    [string]$Environment = "prod",
    [string]$Placeholder = "CHANGE_ME"
)
# "Continue": in Windows PowerShell 5.1, gh writing to stderr would otherwise abort the script.
$ErrorActionPreference = "Continue"

# Required by .github/workflows/.deployer_aca.yml + terragrunt/terragrunt.hcl for prod.
# Deliberately NOT included (must stay unset in prod):
#   AZURE_SEARCH_ENDPOINT/API_KEY, AZURE_STORAGE_ACCOUNT_NAME/KEY/CONTAINER_NAME  -> Terraform creates Search/Storage
#   AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT/KEY                                      -> optional, off in prod
#   REDIS_HOST/PORT/PASSWORD/SSL                                                  -> Terraform creates Managed Redis
#   APPLICATIONINSIGHTS_CONNECTION_STRING                                         -> Terraform creates App Insights
#   AZURE_BLOBSTORAGE_*, AZURE_COSMOS_DB_*, TENANT_PROFILE_*, *_CACHE_TTL_SECONDS -> workflow defaults apply
#   REDIS_TTL_DAYS                                                                -> defaults to 14
# A placeholder in REDIS_PORT / REDIS_TTL_DAYS would break the plan (they are numbers).
$secrets = @(
    "AZURE_CLIENT_ID",
    "AZURE_TENANT_ID",
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_OPENAI_API_KEY"
)
$variables = @(
    "AZURE_CLIENT_ID",
    "RESOURCE_GROUP_NAME",
    "VNET_NAME",
    "VNET_ADDRESS_SPACE",
    "TFSTATE_STORAGE_ACCOUNT",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME",
    "AZURE_SEARCH_INDEX_NAME",
    "CORS_ALLOW_ORIGINS"
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "gh CLI not found. Install it and run 'gh auth login' first." }
gh auth status | Out-Null

$mode = if ($Apply) { "APPLY" } else { "DRY RUN" }
Write-Host "[$mode] $Repo / environment '$Environment'"

# Create the environment if it doesn't exist (needs repo admin).
gh api "repos/$Repo/environments/$Environment" --silent 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  environment '$Environment' missing -> create"
    if ($Apply) { gh api -X PUT "repos/$Repo/environments/$Environment" --silent }
}

$existingSecrets = @()
$existingVars = @()
if ($LASTEXITCODE -eq 0) {
    $existingSecrets = @(gh secret list --repo $Repo --env $Environment --json name --jq ".[].name" 2>$null)
    $existingVars = @(gh variable list --repo $Repo --env $Environment --json name --jq ".[].name" 2>$null)
}

foreach ($name in $secrets) {
    if ($existingSecrets -contains $name) { Write-Host "  secret   $name  (exists, skipped)"; continue }
    Write-Host "  secret   $name  -> create"
    if ($Apply) { gh secret set $name --repo $Repo --env $Environment --body $Placeholder }
}
foreach ($name in $variables) {
    if ($existingVars -contains $name) { Write-Host "  variable $name  (exists, skipped)"; continue }
    Write-Host "  variable $name  -> create"
    if ($Apply) { gh variable set $name --repo $Repo --env $Environment --body $Placeholder }
}

if (-not $Apply) { Write-Host "`nNothing changed. Re-run with -Apply to create the entries." }
else { Write-Host "`nDone. Replace every '$Placeholder' value in Settings > Environments > $Environment before running deploy-aca-prod." }
