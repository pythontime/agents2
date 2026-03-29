---
name: Bug Report
about: Report a bug in the Contoso HR Agent to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
<!-- Clear and concise description of the bug -->

## Which Component?
<!-- Check the area affected -->

- [ ] HR Engine (FastAPI on port 8080)
- [ ] Pipeline (LangGraph / CrewAI agents)
- [ ] Chat Concierge (Alex)
- [ ] Web UI (chat.html / candidates.html / runs.html)
- [ ] MCP Server (FastMCP 2 on port 8081)
- [ ] Knowledge Base (ChromaDB / vectorizer / retriever)
- [ ] Folder Watcher
- [ ] Tests
- [ ] Documentation / Teaching Guides

## Steps to Reproduce

1. Run command: `...`
2. Open page / perform action: `...`
3. Enter value: `...`
4. See error

## Expected Behavior
<!-- What should have happened? -->

## Actual Behavior
<!-- What actually happened? -->

## Error Message
<!-- Paste the full error output -->

```text
Paste error here
```

## Environment

**Operating System:**

- [ ] Windows 11
- [ ] Windows 10
- [ ] macOS (version: )
- [ ] Linux (distro: )

**Shell:**

- [ ] Git Bash
- [ ] PowerShell
- [ ] WSL
- [ ] zsh
- [ ] Other:

**Python Version:**
<!-- Run: python --version -->

```text
```

**Package Manager:**
<!-- Run: uv --version -->

```text
```

**LLM Provider:**

- [ ] Azure AI Foundry (primary -- gpt-4-1-mini)
- [ ] Other (specify: )

**Project Version:**
<!-- Run: git log -1 --oneline -->

```text
```

## Additional Context
<!-- Screenshots, logs, or any other relevant information -->

## Attempted Fixes
<!-- What have you tried so far? -->

- [ ] Checked troubleshooting docs in contoso-hr-agent/README.md
- [ ] Re-seeded knowledge base (`uv run hr-seed`)
- [ ] Reinstalled dependencies (`uv sync`)
- [ ] Verified `.env` configuration (Azure AI Foundry keys)
- [ ] Tried with fresh virtual environment (`uv venv && uv sync`)
- [ ] Searched existing issues

## Impact
<!-- How does this affect your use of the project? -->

- [ ] Blocking - Can't run the project at all
- [ ] Major - Pipeline or chat doesn't work
- [ ] Minor - Small annoyance or cosmetic issue
- [ ] Trivial - Documentation typo or formatting
