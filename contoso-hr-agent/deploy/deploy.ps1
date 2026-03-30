<#
.SYNOPSIS
    Deploy Contoso HR Agent to Azure Container Apps with API Management.

.DESCRIPTION
    One-command PoC deployment using Azure CLI. Deploys:
      - Resource Group (rg-contoso-hr-poc, eastus2)
      - Azure Container Registry (Basic SKU)
      - Container Apps Environment (Consumption)
      - Container App for hr-engine (0.5 CPU / 1Gi, external ingress on 8080)
      - Azure API Management (Consumption tier, no APIs wired)

    Reads secrets from ../. env and passes them as Container App secrets.
    Idempotent: safe to re-run. Uses existing resources if they already exist.

.NOTES
    Run from contoso-hr-agent/ directory:  .\deploy\deploy.ps1
    Teardown:  az group delete --name rg-contoso-hr-poc --yes --no-wait

    Estimated cost: ~$2-4/day (Container Apps Consumption + ACR Basic + APIM Consumption).
    APIM Consumption tier takes 30-45 min to fully activate after creation.
#>

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Make az CLI failures terminate the script (PowerShell doesn't do this by default
# for native commands). Requires PowerShell 7.3+. Silently skip if older.
if ($PSVersionTable.PSVersion.Major -ge 7 -and $PSVersionTable.PSVersion.Minor -ge 3) {
    $PSNativeCommandUseErrorActionPreference = $true
}

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
$RESOURCE_GROUP   = "rg-contoso-hr-poc"
$LOCATION         = "eastus2"
$ACR_NAME         = "contosohrpocacr"     # Must be globally unique, alphanumeric only
$ENV_NAME         = "contoso-hr-env"
$APP_NAME         = "contoso-hr-engine"
$APIM_NAME        = "contoso-hr-apim"
$IMAGE_NAME       = "contoso-hr-agent"
$IMAGE_TAG        = "latest"
$TAGS             = @("purpose=training", "owner=trainer", "auto-delete=true")

# ---------------------------------------------------------------------------
# Helper: Write status messages
# ---------------------------------------------------------------------------
function Write-Step {
    param([string]$Message)
    Write-Host "`n>>> $Message" -ForegroundColor Cyan
}

function Write-Warning-Box {
    param([string]$Message)
    Write-Host "`n!!! $Message" -ForegroundColor Yellow
}

function Get-EnvOrDefault {
    param([hashtable]$Vars, [string]$Key, [string]$Default)
    if ($Vars.ContainsKey($Key) -and -not [string]::IsNullOrWhiteSpace($Vars[$Key])) {
        return $Vars[$Key]
    }
    return $Default
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
Write-Step "Checking Azure CLI login status..."
$account = az account show --output json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Error "Not logged in to Azure CLI. Run 'az login' first."
    exit 1
}
Write-Host "  Logged in as: $($account.user.name)"
Write-Host "  Subscription: $($account.name) ($($account.id))"

# Verify Docker is running (needed for local build; falls back to ACR remote build)
Write-Step "Checking Docker availability..."
try {
    $dockerCheck = docker info 2>&1
    $dockerOk = ($LASTEXITCODE -eq 0)
} catch {
    $dockerOk = $false
}
if (-not $dockerOk) {
    Write-Warning-Box "Docker is not running. Falling back to ACR remote build (az acr build)."
    $USE_ACR_BUILD = $true
} else {
    Write-Host "  Docker is available."
    $USE_ACR_BUILD = $false
}

# ---------------------------------------------------------------------------
# Load environment variables from .env
# ---------------------------------------------------------------------------
Write-Step "Loading environment variables from .env..."
$envFile = Join-Path $PSScriptRoot ".." ".env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found at $envFile. Copy .env.example to .env and fill in values."
    exit 1
}

$envVars = @{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            $envVars[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
}

# Validate required keys
$requiredKeys = @(
    "AZURE_AI_FOUNDRY_ENDPOINT",
    "AZURE_AI_FOUNDRY_KEY",
    "AZURE_AI_FOUNDRY_CHAT_MODEL",
    "AZURE_AI_FOUNDRY_EMBEDDING_MODEL"
)
foreach ($key in $requiredKeys) {
    if (-not $envVars.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($envVars[$key])) {
        Write-Error "Required environment variable '$key' is missing or empty in .env"
        exit 1
    }
}
Write-Host "  Loaded $($envVars.Count) environment variables."

# ---------------------------------------------------------------------------
# Step 1: Resource Group
# ---------------------------------------------------------------------------
Write-Step "Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
az group create `
    --name $RESOURCE_GROUP `
    --location $LOCATION `
    --tags $TAGS `
    --output table

# ---------------------------------------------------------------------------
# Step 2: Azure Container Registry (Basic SKU — ~$0.17/day)
# ---------------------------------------------------------------------------
Write-Step "Creating Azure Container Registry '$ACR_NAME' (Basic SKU)..."
az acr create `
    --resource-group $RESOURCE_GROUP `
    --name $ACR_NAME `
    --sku Basic `
    --admin-enabled true `
    --output table

# Get ACR login server
$acrLoginServer = az acr show --name $ACR_NAME --query loginServer --output tsv
Write-Host "  ACR Login Server: $acrLoginServer"

# ---------------------------------------------------------------------------
# Step 3: Build and push container image
# ---------------------------------------------------------------------------
$fullImageName = "$acrLoginServer/${IMAGE_NAME}:${IMAGE_TAG}"
Write-Step "Building and pushing image '$fullImageName'..."

$dockerContext = Join-Path $PSScriptRoot ".."

if ($USE_ACR_BUILD) {
    # Remote build using ACR Tasks (no local Docker needed)
    # Use --no-logs to avoid az CLI Unicode charmap crash on Windows when streaming uv output.
    # We then poll the ACR run log via az acr task logs instead.
    Write-Host "  Using ACR remote build (az acr build --no-logs)..."
    $buildOutput = az acr build `
        --registry $ACR_NAME `
        --image "${IMAGE_NAME}:${IMAGE_TAG}" `
        --file (Join-Path $PSScriptRoot "Dockerfile") `
        --no-logs `
        --output json `
        $dockerContext | ConvertFrom-Json

    $runId = $buildOutput.runId
    Write-Host "  Build submitted. Run ID: $runId"
    Write-Host "  Waiting for build to complete (this takes ~3-5 minutes)..."

    # Poll until the run finishes
    $maxWait = 600   # 10 minutes max
    $elapsed  = 0
    $interval = 15
    do {
        Start-Sleep -Seconds $interval
        $elapsed += $interval
        $runStatus = az acr task show-run `
            --registry $ACR_NAME `
            --run-id $runId `
            --query "status" --output tsv
        Write-Host "  [$elapsed`s] Build status: $runStatus"
    } while ($runStatus -eq "Running" -and $elapsed -lt $maxWait)

    if ($runStatus -ne "Succeeded") {
        Write-Error "ACR build failed or timed out. Status: $runStatus. Check portal for logs."
        exit 1
    }
    Write-Host "  Build succeeded."
} else {
    # Local Docker build + push
    Write-Host "  Building locally with Docker..."
    az acr login --name $ACR_NAME
    docker build -t $fullImageName -f (Join-Path $PSScriptRoot "Dockerfile") $dockerContext
    docker push $fullImageName
}

# ---------------------------------------------------------------------------
# Step 4: Container Apps Environment (Consumption — pay per use)
# ---------------------------------------------------------------------------
Write-Step "Creating Container Apps Environment '$ENV_NAME'..."
az containerapp env create `
    --resource-group $RESOURCE_GROUP `
    --name $ENV_NAME `
    --location $LOCATION `
    --output table

# ---------------------------------------------------------------------------
# Step 5: Container App (0.5 CPU / 1Gi — minimal for PoC)
# ---------------------------------------------------------------------------
Write-Step "Deploying Container App '$APP_NAME'..."

# Get ACR credentials for image pull
$acrUsername = az acr credential show --name $ACR_NAME --query username --output tsv
$acrPassword = az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv

# Build secrets string: each secret is name=value
# Container Apps secrets must be lowercase and use hyphens (no underscores)
$secrets = @(
    "azure-ai-foundry-endpoint=$($envVars['AZURE_AI_FOUNDRY_ENDPOINT'])",
    "azure-ai-foundry-key=$($envVars['AZURE_AI_FOUNDRY_KEY'])",
    "azure-ai-foundry-chat-model=$($envVars['AZURE_AI_FOUNDRY_CHAT_MODEL'])",
    "azure-ai-foundry-embedding-model=$($envVars['AZURE_AI_FOUNDRY_EMBEDDING_MODEL'])",
    "azure-ai-foundry-api-version=$(Get-EnvOrDefault $envVars 'AZURE_AI_FOUNDRY_API_VERSION' '2024-05-01-preview')",
    "brave-api-key=$(Get-EnvOrDefault $envVars 'BRAVE_API_KEY' 'not-set')",
    "acr-password=$acrPassword"
)
$secretsStr = $secrets -join " "

# Build env vars that reference secrets
$envVarStr = @(
    "AZURE_AI_FOUNDRY_ENDPOINT=secretref:azure-ai-foundry-endpoint",
    "AZURE_AI_FOUNDRY_KEY=secretref:azure-ai-foundry-key",
    "AZURE_AI_FOUNDRY_CHAT_MODEL=secretref:azure-ai-foundry-chat-model",
    "AZURE_AI_FOUNDRY_EMBEDDING_MODEL=secretref:azure-ai-foundry-embedding-model",
    "AZURE_AI_FOUNDRY_API_VERSION=secretref:azure-ai-foundry-api-version",
    "BRAVE_API_KEY=secretref:brave-api-key",
    "LLM_TEMPERATURE=$(Get-EnvOrDefault $envVars 'LLM_TEMPERATURE' '0.2')",
    "LOG_LEVEL=$(Get-EnvOrDefault $envVars 'LOG_LEVEL' 'INFO')",
    "ENGINE_PORT=8080",
    "MCP_PORT=8081",
    "WATCH_POLL_SECONDS=$(Get-EnvOrDefault $envVars 'WATCH_POLL_SECONDS' '3')"
) -join " "

az containerapp create `
    --resource-group $RESOURCE_GROUP `
    --name $APP_NAME `
    --environment $ENV_NAME `
    --image $fullImageName `
    --registry-server $acrLoginServer `
    --registry-username $acrUsername `
    --registry-password $acrPassword `
    --target-port 8080 `
    --ingress external `
    --min-replicas 0 `
    --max-replicas 1 `
    --cpu 0.5 `
    --memory 1Gi `
    --secrets $secretsStr `
    --env-vars $envVarStr `
    --output table

# ---------------------------------------------------------------------------
# Step 6: Azure API Management (Consumption tier — ~$3.50/million calls)
# ---------------------------------------------------------------------------
Write-Step "Creating API Management instance '$APIM_NAME' (Consumption tier)..."
Write-Warning-Box "APIM Consumption tier takes 30-45 minutes to fully activate. Deployment will continue in the background."

# APIM Consumption requires an email and org name
az apim create `
    --resource-group $RESOURCE_GROUP `
    --name $APIM_NAME `
    --publisher-name "Contoso HR Training" `
    --publisher-email "$($account.user.name)" `
    --sku-name Consumption `
    --location $LOCATION `
    --no-wait `
    --output table

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Step "Deployment complete!"

$appFqdn = az containerapp show `
    --resource-group $RESOURCE_GROUP `
    --name $APP_NAME `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Green
Write-Host "  CONTOSO HR AGENT - PoC Deployment Summary" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Resource Group:  $RESOURCE_GROUP"
Write-Host "  Location:        $LOCATION"
Write-Host ""
Write-Host "  Container App:   https://$appFqdn" -ForegroundColor White
Write-Host "  Web UI:          https://$appFqdn/chat.html" -ForegroundColor White
Write-Host "  API Docs:        https://$appFqdn/docs" -ForegroundColor White
Write-Host "  Health Check:    https://$appFqdn/api/health" -ForegroundColor White
Write-Host ""
Write-Host "  ACR Registry:    $acrLoginServer"
Write-Host "  APIM Instance:   $APIM_NAME (provisioning in background, 30-45 min)"
Write-Host ""
Write-Host "  Estimated Cost:  ~`$2-4/day" -ForegroundColor Yellow
Write-Host "    ACR Basic:     ~`$0.17/day" -ForegroundColor DarkGray
Write-Host "    Container App: ~`$0-2/day (Consumption, scales to zero)" -ForegroundColor DarkGray
Write-Host "    APIM:          ~`$0/day (Consumption, pay per call)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  CLEANUP (deletes everything):" -ForegroundColor Red
Write-Host "    az group delete --name $RESOURCE_GROUP --yes --no-wait" -ForegroundColor Red
Write-Host ""
Write-Host "  NOTE: First request may take 30-60s (container cold start + ChromaDB seeding)." -ForegroundColor Yellow
Write-Host "  NOTE: APIM is still provisioning. Check status in Azure Portal:" -ForegroundColor Yellow
Write-Host "         Portal > Resource Groups > $RESOURCE_GROUP > $APIM_NAME" -ForegroundColor Yellow
Write-Host ""
