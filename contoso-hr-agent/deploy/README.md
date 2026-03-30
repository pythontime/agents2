# Contoso HR Agent -- Azure Container Apps PoC Deployment

## What Gets Deployed

| Resource | SKU / Tier | Estimated Cost | Purpose |
|----------|-----------|----------------|---------|
| Resource Group | `rg-contoso-hr-poc` | Free | Single-group teardown |
| Container Registry | Basic | ~$0.17/day | Stores the Docker image |
| Container Apps Env | Consumption | ~$0/day (idle) | Serverless container hosting |
| Container App | 0.5 CPU / 1Gi | ~$0-2/day | Runs hr-engine (FastAPI on 8080) |
| API Management | Consumption | ~$0/day (pay per call) | Future Entra ID auth gateway |

**Total estimated cost: ~$2-4/day when active, under $1/day when idle.**

## Prerequisites

- Azure CLI installed and logged in (`az login`)
- Docker Desktop running (or the script falls back to ACR remote build)
- `.env` file populated with Azure AI Foundry credentials

## Deploy

From the `contoso-hr-agent/` directory:

```powershell
.\deploy\deploy.ps1
```

The script will print URLs when complete. First request takes 30-60 seconds (cold start + ChromaDB seeding).

## Verify

After deployment, check these URLs (printed by the script):

- **Health check:** `https://<app-fqdn>/api/health`
- **Web UI:** `https://<app-fqdn>/chat.html`
- **API docs:** `https://<app-fqdn>/docs`
- **Candidates:** `https://<app-fqdn>/candidates.html`
- **Pipeline Runs:** `https://<app-fqdn>/runs.html`

## Teardown

Single command destroys everything:

```powershell
az group delete --name rg-contoso-hr-poc --yes --no-wait
```

## Architecture Notes

### What works in this PoC

- FastAPI engine with all API endpoints and web UI
- Chat with "Alex" (ChatConcierge agent)
- Resume upload and evaluation pipeline
- ChromaDB knowledge base (re-seeded on each container start)

### Known PoC limitations

- **ChromaDB is ephemeral:** Stored in container filesystem, lost on restart. OK for demos.
- **SQLite is ephemeral:** Same caveat. Candidate evaluations reset on restart.
- **No MCP server:** Only hr-engine is deployed (port 8080). The MCP SSE server (port 8081) is not exposed. To add it, deploy a second Container App or add a second container to the same app.
- **No authentication:** Container App ingress is open. This is intentional for PoC.
- **Scale to zero:** Min replicas is 0, so the app may cold-start after idle periods (~30s).

### APIM Next Steps (Entra ID Auth)

The API Management instance is deployed but has no APIs wired. To add Entra ID authentication:

1. **Wait for APIM to finish provisioning** (30-45 min after deployment).
2. **Register an App in Entra ID:**
   - Portal > Entra ID > App registrations > New registration
   - Set redirect URI to `https://<apim-name>.azure-api.net/signin-oidc`
   - Note the Application (client) ID and create a client secret
3. **Add the Container App as an APIM backend:**
   ```
   az apim api create --resource-group rg-contoso-hr-poc \
     --service-name contoso-hr-apim \
     --api-id contoso-hr-api \
     --path /hr \
     --display-name "Contoso HR API" \
     --service-url https://<app-fqdn>
   ```
4. **Add a validate-jwt inbound policy** on the API to require Entra ID tokens.
5. **Lock down Container App ingress** to only accept traffic from APIM (via IP restriction or VNet integration).

### Production Differences

If this were production, you would change:

- **ChromaDB** -> Azure AI Search or Cosmos DB for persistent vector storage
- **SQLite** -> Azure SQL Serverless or Cosmos DB Serverless
- **Container Apps** -> min replicas 1 (avoid cold starts), 1+ CPU / 2Gi memory
- **ACR** -> Standard SKU with geo-replication
- **APIM** -> Developer or Standard tier for SLA
- **Authentication** -> Entra ID via APIM validate-jwt policy (see above)
- **Networking** -> VNet integration, private endpoints for ACR/AI Services
- **Monitoring** -> Application Insights, Log Analytics workspace
- **CI/CD** -> GitHub Actions with OIDC federated credentials (no stored secrets)
