#!/bin/bash

# Azure CLI Script to Configure Managed Identity for GitHub Actions OIDC
# This script creates a user-assigned managed identity and configures federated identity credentials
# for GitHub Actions OIDC authentication following Azure security best practices

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Configure managed identity for GitHub Actions OIDC authentication.

Options:
    -g, --resource-group        Resource group name (required)
    -n, --identity-name         Managed identity name (required)
    -r, --github-repo           GitHub repository in format owner/repo (required)
    -e, --environment           GitHub environment name (required)
    --storage-account           Storage account name for Terraform state (optional, default: auto-generated)
    --storage-container         Storage container name for Terraform state (optional, default: tfstate)
    --create-storage            Create storage account for Terraform state (flag)
    --dry-run                   Show what would be done without making changes
    -h, --help                  Show this help message

Examples:
    # Basic setup for main branch
    $0 -g myResourceGroup -n myManagedIdentity -r myorg/myrepo

    # Setup for specific environment
    $0 -g myResourceGroup -n myManagedIdentity -r myorg/myrepo -e production

    # Setup with Terraform state storage account
    $0 -g myResourceGroup -n myManagedIdentity -r myorg/myrepo --create-storage

    # Setup with custom storage account name
    $0 -g myResourceGroup -n myManagedIdentity -r myorg/myrepo --create-storage --storage-account mystorageaccount

    # Dry run to see what would be done
    $0 -g myResourceGroup -n myManagedIdentity -r myorg/myrepo --dry-run
EOF
}

# Default values
GITHUB_ENVIRONMENT=""
STORAGE_ACCOUNT="" # Will be generated based on repo name
STORAGE_CONTAINER="tfstate"
CREATE_STORAGE=false
DRY_RUN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -n|--identity-name)
            IDENTITY_NAME="$2"
            shift 2
            ;;
        -r|--github-repo)
            GITHUB_REPO="$2"
            shift 2
            ;;
        -e|--environment)
            GITHUB_ENVIRONMENT="$2"
            shift 2
            ;;
        --storage-account)
            STORAGE_ACCOUNT="$2"
            shift 2
            ;;
        --storage-container)
            STORAGE_CONTAINER="$2"
            shift 2
            ;;
        --create-storage)
            CREATE_STORAGE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "${RESOURCE_GROUP:-}" || -z "${IDENTITY_NAME:-}" || -z "${GITHUB_REPO:-}" || -z "${GITHUB_ENVIRONMENT:-}" ]]; then
    log_error "Required parameters missing. Use -h for help."
    exit 1
fi

# Validate GitHub repository format
if [[ ! "$GITHUB_REPO" =~ ^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$ ]]; then
    log_error "Invalid GitHub repository format. Expected: owner/repo"
    exit 1
fi

# Function to execute commands with dry-run support
execute_command() {
    local cmd="$1"
    local description="$2"
    
    log_info "$description"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "    [DRY-RUN] Would execute: $cmd"
        return 0
    else
        echo "    Executing: $cmd"
        eval "$cmd"
        return $?
    fi
}

# Function to generate randomized storage account name
generate_storage_account_name() {
    if [[ -z "$STORAGE_ACCOUNT" ]]; then
        # Extract and sanitize repo name and environment name
        local repo_name=$(echo "$GITHUB_REPO" | cut -d'/' -f2 | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
        local env_name=$(echo "$GITHUB_ENVIRONMENT" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')

        # Use only the first 6 characters of the sanitized environment name
        local env_prefix="${env_name:0:6}"

        # Calculate max repo name length to fit within 24 chars: tfstate (7) + repo + env_prefix (6)
        local max_length=24
        local tfstate_len=7
        local env_prefix_len=6
        local max_repo_len=$((max_length - tfstate_len - env_prefix_len))
        local repo_trimmed="$repo_name"
        if [[ ${#repo_name} -gt $max_repo_len ]]; then
            repo_trimmed="${repo_name:0:$max_repo_len}"
        fi

        # Compose base name: tfstate + trimmed repo + env_prefix
        local base_name="tfstate${repo_trimmed}${env_prefix}"

        STORAGE_ACCOUNT="$base_name"

        # Final validation to ensure only lowercase letters and numbers
        STORAGE_ACCOUNT=$(echo "$STORAGE_ACCOUNT" | sed 's/[^a-z0-9]//g')

        # Ensure minimum length
        if [[ ${#STORAGE_ACCOUNT} -lt 3 ]]; then
            STORAGE_ACCOUNT="${STORAGE_ACCOUNT}abc"
        fi

        log_info "Generated storage account name: $STORAGE_ACCOUNT (based on repo: $repo_trimmed, environment prefix: $env_prefix)"
    fi
}

# Function to check if Azure CLI is installed and user is logged in
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    # Check if user is logged in
    if ! az account show &> /dev/null; then
        log_error "Not logged in to Azure. Please run 'az login' first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}



# Function to check if resource group exists
check_resource_group() {
    log_info "Checking if resource group '$RESOURCE_GROUP' exists..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
            log_error "Resource group '$RESOURCE_GROUP' does not exist. Please create it first or use an existing one."
            exit 1
        fi
        log_success "Resource group '$RESOURCE_GROUP' exists"
    else
        log_info "[DRY-RUN] Would check if resource group '$RESOURCE_GROUP' exists"
    fi
}

# Function to create user-assigned managed identity
create_managed_identity() {
    log_info "Creating user-assigned managed identity '$IDENTITY_NAME'..."
    
    # Check if identity already exists
    if [[ "$DRY_RUN" == "false" ]]; then
        if az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_warning "Managed identity '$IDENTITY_NAME' already exists. Skipping creation."
            return 0
        fi
    fi
    
    execute_command "az identity create --name '$IDENTITY_NAME' --resource-group '$RESOURCE_GROUP'" \
        "Creating user-assigned managed identity"
    
    log_success "Managed identity '$IDENTITY_NAME' created successfully"
}

# Function to get managed identity details
get_identity_details() {
    log_info "Retrieving managed identity details..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        CLIENT_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "clientId" --output tsv)
        PRINCIPAL_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "principalId" --output tsv)
        IDENTITY_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "id" --output tsv)
        
        log_info "Client ID: $CLIENT_ID"
        log_info "Principal ID: $PRINCIPAL_ID"
        log_info "Identity ID: $IDENTITY_ID"
    else
        log_info "[DRY-RUN] Would retrieve managed identity details"
        CLIENT_ID="[DRY-RUN-CLIENT-ID]"
        PRINCIPAL_ID="[DRY-RUN-PRINCIPAL-ID]"
        IDENTITY_ID="[DRY-RUN-IDENTITY-ID]"
    fi
}


# Function to create federated identity credentials
create_federated_credentials() {
    log_info "Creating federated identity credentials for GitHub Actions OIDC..."
    
    # Always create subject claim for environment-specific deployments
    SUBJECT="repo:$GITHUB_REPO:environment:$GITHUB_ENVIRONMENT"
    CREDENTIAL_NAME="github-$GITHUB_ENVIRONMENT"
    
    # GitHub Actions OIDC issuer and audience
    ISSUER="https://token.actions.githubusercontent.com"
    AUDIENCE="api://AzureADTokenExchange"
    
    log_info "Subject: $SUBJECT"
    log_info "Issuer: $ISSUER"
    log_info "Audience: $AUDIENCE"
    
    # Check if federated credential already exists
    if [[ "$DRY_RUN" == "false" ]]; then
        if az identity federated-credential show --name "$CREDENTIAL_NAME" --identity-name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_warning "Federated credential '$CREDENTIAL_NAME' already exists. Updating..."
            execute_command "az identity federated-credential update --name '$CREDENTIAL_NAME' --identity-name '$IDENTITY_NAME' --resource-group '$RESOURCE_GROUP' --issuer '$ISSUER' --subject '$SUBJECT' --audience '$AUDIENCE'" \
                "Updating federated identity credential"
        else
            execute_command "az identity federated-credential create --name '$CREDENTIAL_NAME' --identity-name '$IDENTITY_NAME' --resource-group '$RESOURCE_GROUP' --issuer '$ISSUER' --subject '$SUBJECT' --audience '$AUDIENCE'" \
                "Creating federated identity credential"
        fi
    else
        execute_command "az identity federated-credential create --name '$CREDENTIAL_NAME' --identity-name '$IDENTITY_NAME' --resource-group '$RESOURCE_GROUP' --issuer '$ISSUER' --subject '$SUBJECT' --audience '$AUDIENCE'" \
            "Creating federated identity credential"
    fi
    
    log_success "Federated identity credentials created successfully"
}

# Function to display GitHub Actions configuration
display_github_actions_config() {
    log_info "GitHub Actions Configuration:"
    
    cat << EOF

Add the following secrets and variables to your GitHub repository environment ($GITHUB_REPO):
Go to Settings > Secrets and variables > Actions

Environment Secrets:
- AZURE_CLIENT_ID: $CLIENT_ID
- AZURE_SUBSCRIPTION_ID: $(az account show --query "id" --output tsv 2>/dev/null || echo "[SUBSCRIPTION-ID]")
- AZURE_TENANT_ID: $(az account show --query "tenantId" --output tsv 2>/dev/null || echo "[TENANT-ID]")

Environment Variables:
- APIM_SUBNET_PREFIX: CIDR for APIM subnet (e.g., 10.46.8.0/26)
- APP_SERVICE_SUBNET_PREFIX: CIDR for App Service subnet (e.g., 10.46.8.64/26)
- PRIVATEENDPOINT_SUBNET_PREFIX: CIDR for Private Endpoint subnet (e.g., 10.46.8.128/26)
- RESOURCE_GROUP_NAME: Name of the Azure Resource Group to host the Azure Resources (e.g., a9cee3-test-networking)
- TF_STATE_STORAGE_ACCOUNT: Name of the storage account for Terraform state
- VNET_NAME: Name of the Azure vNet

Managed Identity Details:
- Name: $IDENTITY_NAME
- Resource Group: $RESOURCE_GROUP
- Client ID: $CLIENT_ID
- Principal ID: $PRINCIPAL_ID
- Identity ID: $IDENTITY_ID

Storage Account Details:
- Name: $STORAGE_ACCOUNT
- Resource Group: $RESOURCE_GROUP
- Container: $STORAGE_CONTAINER
- Authentication: Azure AD (no storage keys required)

EOF
}

# Function to create storage account for Terraform state
create_terraform_storage() {
    if [[ "$CREATE_STORAGE" != "true" ]]; then
        return 0
    fi
    
    log_info "Creating storage account for Terraform state..."
    
    # Validate storage account name
    if [[ ${#STORAGE_ACCOUNT} -lt 3 || ${#STORAGE_ACCOUNT} -gt 24 ]]; then
        log_error "Storage account name must be between 3 and 24 characters long"
        exit 1
    fi
    
    if [[ ! "$STORAGE_ACCOUNT" =~ ^[a-z0-9]+$ ]]; then
        log_error "Storage account name must contain only lowercase letters and numbers"
        exit 1
    fi
    
    # Check if storage account already exists
    if [[ "$DRY_RUN" == "false" ]]; then
        if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_warning "Storage account '$STORAGE_ACCOUNT' already exists. Skipping creation."
            return 0
        fi
    fi
    
    # Create storage account with secure defaults
 execute_command "az storage account create \
    --name '$STORAGE_ACCOUNT' \
    --resource-group '$RESOURCE_GROUP' \
    --location '$(az group show --name $RESOURCE_GROUP --query location --output tsv)' \
    --sku 'Standard_LRS' \
    --kind 'StorageV2' \
    --access-tier 'Hot' \
    --min-tls-version 'TLS1_2' \
    --allow-blob-public-access false \
    --default-action 'Allow' \
    --bypass 'AzureServices' \
    --https-only true \
    --enable-local-user false \
    --allow-shared-key-access false" \
        "Creating storage account with public blob access for tfstate"
    
    # Enable versioning for better state management
    execute_command "az storage account blob-service-properties update \
        --account-name '$STORAGE_ACCOUNT' \
        --resource-group '$RESOURCE_GROUP' \
        --enable-versioning true" \
        "Enabling blob versioning for Terraform state"
    
    # Create container for Terraform state
    execute_command "az storage container create \
        --name '$STORAGE_CONTAINER' \
        --account-name '$STORAGE_ACCOUNT' \
        --auth-mode login" \
        "Creating storage container for Terraform state"
    
    log_success "Storage account '$STORAGE_ACCOUNT' created successfully"
}

# Function to assign storage-specific roles to managed identity
assign_storage_roles() {
    if [[ "$CREATE_STORAGE" != "true" ]]; then
        return 0
    fi
    
    log_info "Assigning storage-specific roles to managed identity..."
    
    # Get storage account resource ID
    if [[ "$DRY_RUN" == "false" ]]; then
        STORAGE_ACCOUNT_ID=$(az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --query "id" --output tsv)
    else
        STORAGE_ACCOUNT_ID="[DRY-RUN-STORAGE-ACCOUNT-ID]"
    fi
    
    # Required roles for Terraform state management
    STORAGE_ROLES=(
        "Storage Blob Data Contributor"
        "Storage Account Contributor"
    )
    
    for role in "${STORAGE_ROLES[@]}"; do
        execute_command "az role assignment create \
            --assignee '$CLIENT_ID' \
            --role '$role' \
            --scope '$STORAGE_ACCOUNT_ID'" \
            "Assigning '$role' role for storage account"
    done
    
    log_success "Storage roles assigned successfully"
}

# Function to verify setup
verify_setup() {
    log_info "Verifying setup..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Check if identity exists
        if az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_success "✓ Managed identity exists"
        else
            log_error "✗ Managed identity not found"
            return 1
        fi
        
        # Check if federated credential exists
        if az identity federated-credential show --name "$CREDENTIAL_NAME" --identity-name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_success "✓ Federated credential exists"
        else
            log_error "✗ Federated credential not found"
            return 1
        fi
        
        # Check role assignments
        ROLE_COUNT=$(az role assignment list --assignee "$CLIENT_ID" --query "length(@)" --output tsv)
        if [[ "$ROLE_COUNT" -gt 0 ]]; then
            log_success "✓ Role assignments configured ($ROLE_COUNT roles)"
        else
            log_warning "! No role assignments found"
        fi
        
        # Check storage account if created
        if [[ "$CREATE_STORAGE" == "true" ]]; then
            if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
                log_success "✓ Storage account exists"
                
                # Check if container exists
                if az storage container show --name "$STORAGE_CONTAINER" --account-name "$STORAGE_ACCOUNT" --auth-mode login &> /dev/null; then
                    log_success "✓ Storage container exists"
                else
                    log_error "✗ Storage container not found"
                    return 1
                fi
            else
                log_error "✗ Storage account not found"
                return 1
            fi
        fi
    else
        log_info "[DRY-RUN] Would verify setup"
    fi
    
    log_success "Setup verification completed"
}

# Main execution
main() {
    log_info "Starting GitHub Actions OIDC setup for Azure..."
    log_info "Repository: $GITHUB_REPO"
    log_info "Environment: $GITHUB_ENVIRONMENT"

    check_prerequisites
    check_resource_group

    # Generate storage account name if creating storage
    if [[ "$CREATE_STORAGE" == "true" ]]; then
        generate_storage_account_name
        log_info "Creating Terraform state storage: $STORAGE_ACCOUNT"
    fi

    create_managed_identity
    get_identity_details

    # Add a short delay to allow Azure to propagate the new identity if needed
    if [[ "$DRY_RUN" == "false" ]]; then
        log_info "Waiting 10 seconds for managed identity propagation..."
        sleep 10
    fi
    create_terraform_storage
    assign_storage_roles
    create_federated_credentials
    verify_setup

    if [[ "$DRY_RUN" == "false" ]]; then
        display_github_actions_config
    fi

    log_success "GitHub Actions OIDC setup completed successfully!"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "This was a dry run. No actual changes were made."
        log_info "Run the script without --dry-run to apply the changes."
    fi
}

# Run main function
main "$@"
