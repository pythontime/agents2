# Security Policy

## Supported Versions

This is an educational project for O'Reilly Live Learning courses. The active project is `contoso-hr-agent/`. We maintain security updates for the current version only.

| Version | Supported |
| ------- | --------- |
| main (contoso-hr-agent/) | Yes |
| oreilly-agent-mvp/ (legacy) | No |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

**For security issues:**

- **Email:** [tim@techtrainertim.com](mailto:tim@techtrainertim.com)
- **Subject:** [SECURITY] agents2 vulnerability report
- **Include:** Description, steps to reproduce, potential impact

**Response timeline:**

- Initial response: Within 48 hours
- Status update: Within 5 business days
- Resolution target: 30 days for critical issues

## Security Best Practices for Users

This project demonstrates AI agent patterns and requires API keys for Azure AI Foundry and optionally Brave Search. Please follow these guidelines:

### API Key Management

- **DO** use environment variables (`.env` file)
- **DO** add `.env` to `.gitignore` (already configured)
- **DO** rotate keys regularly
- **DON'T** commit API keys to version control
- **DON'T** share keys in screenshots or logs
- **DON'T** use production keys for demos

### Required Environment Variables

The following secrets are configured in `.env` (see `.env.example`):

- `AZURE_AI_FOUNDRY_ENDPOINT` -- Azure AI Foundry endpoint URL
- `AZURE_AI_FOUNDRY_KEY` -- Azure AI Foundry API key
- `AZURE_AI_FOUNDRY_CHAT_MODEL` -- Chat model deployment name
- `AZURE_AI_FOUNDRY_EMBEDDING_MODEL` -- Embedding model deployment name
- `BRAVE_API_KEY` -- Brave Search API key (optional, for ResumeAnalystAgent web search)

### Recommended Practices

1. **Use separate API keys** for development and production
2. **Enable rate limiting** on your Azure AI Foundry deployments
3. **Monitor API usage** to detect unauthorized access
4. **Review logs** for sensitive data before sharing (resume content may contain PII)
5. **Keep dependencies updated** (`uv sync` to get latest compatible versions)

## Known Security Considerations

### LLM API Calls

- Resume data and HR policy content is sent to Azure AI Foundry for processing
- Ensure compliance with your organization's data policies before processing real resumes
- The ChatConciergeAgent (Alex) sends user messages and session context to the LLM
- Consider using Azure AI Foundry with data residency controls for enterprise compliance

### Resume Data (PII)

- Sample resumes in `sample_resumes/` contain fictional data only
- If processing real resumes, be aware of PII regulations (GDPR, CCPA, etc.)
- Evaluation results are stored locally in `data/hr.db` (SQLite) and `data/outgoing/` (JSON)
- Chat sessions are stored in `data/chat_sessions/` as JSON files
- The `data/` directory is gitignored and should never be committed

### ChromaDB Knowledge Base

- Policy documents in `sample_knowledge/` are embedded and stored in `data/chroma/`
- Embeddings are generated via Azure AI Foundry (text-embedding-3-large)
- The ChromaDB data directory is local and gitignored

### Port Exposure

- The HR engine runs on port 8080 (localhost by default)
- The MCP server runs on port 8081/sse (localhost by default)
- Both use `force_kill_port()` on startup to clear conflicting processes
- Do not expose these ports to the public internet without proper authentication

### Dependencies

- We regularly update dependencies for security patches
- Run `uv sync` to get the latest compatible versions
- Review `pyproject.toml` for current dependency specifications

## Disclosure Policy

- Security issues are addressed promptly
- Fixes are released as soon as possible
- Credit is given to reporters (unless anonymity is requested)
- CVEs will be filed for critical vulnerabilities

## Contact

**Tim Warner**
Email: [tim@techtrainertim.com](mailto:tim@techtrainertim.com)
Website: [TechTrainerTim.com](https://TechTrainerTim.com)

For general questions, use [GitHub Issues](https://github.com/timothywarner-org/agents2/issues).
For security concerns, use email (see above).

---

This project is for educational purposes. Use in production environments at your own risk.
