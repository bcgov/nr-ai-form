#!/bin/bash

# Script to set up GitHub repository variables for Terraform backend configuration
# This script uses GitHub CLI to set repository variables

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Set up GitHub repository variables for Terraform backend configuration.

Options:
    -r, --repo                  GitHub repository in format owner/repo (required)
    -g, --resource-group        Resource group name for Terraform state (required)
    -s, --storage-account       Storage account name for Terraform state (required)
    -c, --container             Storage container name (optional, default: tfstate)
    -k, --key                   State file key (optional, default: terraform.tfstate)
    -e, --environment           GitHub environment name (optional)
    -h, --help                  Show this help message

Examples:
    $0 -r owner/repo -g rg-tfstate-prod -s sttfstateprod
    $0 -r owner/repo -g rg-tfstate-dev -s sttfstatedev -e development
EOF
}

# Default values
CONTAINER_NAME="tfstate"
STATE_KEY="terraform.tfstate"
ENVIRONMENT=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--repo)
            GITHUB_REPO="$2"
            shift 2
            ;;
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -s|--storage-account)
            STORAGE_ACCOUNT="$2"
            shift 2
            ;;
        -c|--container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -k|--key)
            STATE_KEY="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
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
if [[ -z "${GITHUB_REPO:-}" ]]; then
    log_error "GitHub repository is required"
    usage
    exit 1
fi

if [[ -z "${RESOURCE_GROUP:-}" ]]; then
    log_error "Resource group is required"
    usage
    exit 1
fi

if [[ -z "${STORAGE_ACCOUNT:-}" ]]; then
    log_error "Storage account is required"
    usage
    exit 1
fi

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) is required but not installed"
    log_info "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if user is authenticated with GitHub CLI
if ! gh auth status &> /dev/null; then
    log_error "You must be authenticated with GitHub CLI"
    log_info "Run: gh auth login"
    exit 1
fi

log_info "Setting up GitHub repository variables for Terraform backend..."

# Set variables based on environment
if [[ -n "$ENVIRONMENT" ]]; then
    log_info "Setting environment-specific variables for environment: $ENVIRONMENT"
    
    # Set environment variables
    gh variable set TF_STATE_RESOURCE_GROUP --body "$RESOURCE_GROUP" --repo "$GITHUB_REPO" --env "$ENVIRONMENT"
    gh variable set TF_STATE_STORAGE_ACCOUNT --body "$STORAGE_ACCOUNT" --repo "$GITHUB_REPO" --env "$ENVIRONMENT"
    gh variable set TF_STATE_CONTAINER --body "$CONTAINER_NAME" --repo "$GITHUB_REPO" --env "$ENVIRONMENT"
    gh variable set TF_STATE_KEY --body "$STATE_KEY" --repo "$GITHUB_REPO" --env "$ENVIRONMENT"
    
    log_success "Environment variables set for environment: $ENVIRONMENT"
else
    log_info "Setting repository-level variables"
    
    # Set repository variables
    gh variable set TF_STATE_RESOURCE_GROUP --body "$RESOURCE_GROUP" --repo "$GITHUB_REPO"
    gh variable set TF_STATE_STORAGE_ACCOUNT --body "$STORAGE_ACCOUNT" --repo "$GITHUB_REPO"
    gh variable set TF_STATE_CONTAINER --body "$CONTAINER_NAME" --repo "$GITHUB_REPO"
    gh variable set TF_STATE_KEY --body "$STATE_KEY" --repo "$GITHUB_REPO"
    
    log_success "Repository variables set"
fi

log_info "Current variables:"
if [[ -n "$ENVIRONMENT" ]]; then
    gh variable list --repo "$GITHUB_REPO" --env "$ENVIRONMENT" || true
else
    gh variable list --repo "$GITHUB_REPO" || true
fi

log_success "GitHub repository variables configured successfully!"
log_info "You can now use these variables in your GitHub Actions workflow."
