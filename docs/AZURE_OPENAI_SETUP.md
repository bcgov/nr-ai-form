# Azure OpenAI Configuration for Deployment

## Overview
The backend application requires Azure OpenAI credentials to function. These are now configured to be passed through the deployment pipeline into the Azure App Service as environment variables.

## Required GitHub Secrets

You need to configure the following secrets in your GitHub repository:

### Navigate to: Repository Settings → Secrets and variables → Actions → Secrets

Add these **Repository Secrets**:

1. **`AZURE_OPENAI_API_KEY`** (Required)
   - Your Azure OpenAI API key
   - Keep this secret and secure
   - Example: `abcd1234efgh5678ijkl9012mnop3456`

2. **`AZURE_OPENAI_ENDPOINT`** (Required)
   - Your Azure OpenAI endpoint URL
   - Format: `https://your-resource-name.openai.azure.com`
   - Example: `https://my-openai-resource.openai.azure.com`

3. **`AZURE_OPENAI_DEPLOYMENT_NAME`** (Required)
   - The name of your deployed model in Azure OpenAI
   - Example: `gpt-4` or `gpt-35-turbo`

### Repository Variables

Add this **Repository Variable**:

1. **`AZURE_OPENAI_API_VERSION`** (Optional - has default)
   - The Azure OpenAI API version
   - Default: `2024-10-21`
   - Only add if you need a different version

## How It Works

### Deployment Flow:
```
GitHub Secrets/Variables
    ↓
GitHub Actions Workflow (.deployer.yml)
    ↓
Terragrunt Configuration
    ↓
Terraform (infra/main.tf)
    ↓
Azure App Service (Environment Variables)
    ↓
Backend Application (Python code)
```

### Files Modified:

1. **`.github/workflows/.deployer.yml`**
   - Passes environment variables from GitHub to Terragrunt

2. **`terragrunt/terragrunt.hcl`**
   - Reads environment variables and generates Terraform variables

3. **`infra/variables.tf`**
   - Defines the root-level variables

4. **`infra/main.tf`**
   - Passes variables to the API module

5. **`infra/modules/api/variables.tf`**
   - Defines module-level variables

6. **`infra/modules/api/main.tf`**
   - Configures Azure App Service with environment variables

## Testing Locally

To test the Docker container locally with your Azure OpenAI credentials:

```bash
# Create a .env file in the backend directory
cd backend
cp env.example .env

# Edit .env and add your credentials:
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Build and run the Docker container
docker build -t nr-ai-backend:local .
docker run -p 8000:8000 --env-file .env nr-ai-backend:local
```

## Verification

After deployment, you can verify the environment variables are set in Azure App Service:

1. Go to Azure Portal
2. Navigate to your App Service
3. Go to **Configuration** → **Application settings**
4. Check that these variables are present:
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_VERSION`
   - `AZURE_OPENAI_DEPLOYMENT_NAME`

## Security Notes

- ✅ API keys are stored as GitHub Secrets (encrypted)
- ✅ Terraform marks sensitive variables as `sensitive = true`
- ✅ Environment variables are injected at runtime, not baked into Docker images
- ✅ Keys are never exposed in logs or repository files

## Troubleshooting

### Error: "Missing credentials. Please pass one of `api_key`..."

**Cause**: The environment variables are not set or not reaching the application.

**Solution**:
1. Check GitHub Secrets are configured correctly
2. Verify the deployment workflow ran successfully
3. Check Azure App Service configuration in portal
4. Restart the App Service after adding variables

### Error: "ModuleNotFoundError: No module named 'backend'"

**Cause**: Docker container structure issue (already fixed in Dockerfile).

**Solution**: This has been resolved by updating the Dockerfile to properly structure the Python module paths.

## Additional Environment Variables (Optional)

If you need additional configuration, you can add these to your backend/.env file or Azure App Service:

- `LANGCHAIN_TRACING_V2` - Enable LangChain tracing
- `LANGCHAIN_API_KEY` - LangChain API key
- `DEBUG` - Enable debug mode (true/false)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

