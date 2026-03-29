# Pull Request

## Description
<!-- Provide a brief description of your changes -->

## Type of Change
<!-- Check all that apply -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Code style/formatting
- [ ] Refactoring (no functional changes)
- [ ] Teaching improvement (better examples, clearer explanations)
- [ ] Test addition or update

## Component Affected
<!-- Check all that apply -->

- [ ] Pipeline (pipeline/graph.py, agents.py, tasks.py, tools.py, prompts.py)
- [ ] Chat Concierge (Alex)
- [ ] Web UI (chat.html / candidates.html / runs.html)
- [ ] MCP Server (mcp_server/)
- [ ] Knowledge Base (knowledge/vectorizer.py, retriever.py)
- [ ] Engine (engine.py -- FastAPI)
- [ ] Folder Watcher (watcher/)
- [ ] Models (models.py)
- [ ] Config (config.py)
- [ ] Tests
- [ ] Documentation / Teaching Guides

## Related Issues
<!-- Link to related issues using #issue_number -->

Closes #
Related to #

## Changes Made
<!-- Describe what you changed and why -->

-
-
-

## Testing
<!-- Describe how you tested these changes -->

- [ ] Ran `uv run pytest tests/ -v` successfully
- [ ] Ran `uv run ruff check src/ tests/` with no errors
- [ ] Tested pipeline with sample resume upload via web UI
- [ ] Tested chat with Alex via web UI
- [ ] Verified parallel pipeline execution on runs.html
- [ ] Verified candidates appear on candidates.html
- [ ] Tested MCP server with MCP Inspector
- [ ] Verified documentation renders correctly

**Test results:**

```text
Paste relevant output here
```

## Screenshots
<!-- If applicable, add screenshots to help explain your changes -->

## Checklist
<!-- Check all that apply -->

- [ ] My code follows the [style guidelines](../CONTRIBUTING.md#code-standards)
- [ ] I have performed a self-review of my code
- [ ] I have commented my code where needed
- [ ] I have updated relevant documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally
- [ ] Any dependent changes have been merged
- [ ] No secrets or API keys are included in the changes

## Educational Impact
<!-- For teaching-related changes -->

- [ ] Maintains beginner-friendly approach
- [ ] Doesn't complicate setup process
- [ ] Enhances learning experience
- [ ] Includes clear examples
- [ ] Preserves the parallel pipeline demo as a teaching tool

## Additional Notes
<!-- Any other information that reviewers should know -->

---

**Thank you for contributing to the Contoso HR Agent!**

Your changes help learners worldwide understand production AI agent patterns.
