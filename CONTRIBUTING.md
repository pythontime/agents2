# Contributing to agents2

Thank you for your interest in contributing to this O'Reilly Live Learning project!

This repository demonstrates AI agent patterns for educational purposes. The primary project is `contoso-hr-agent/`, a Contoso HR Agent that screens Microsoft Certified Trainer resumes using LangGraph, CrewAI, and Azure AI Foundry. We welcome contributions that improve the learning experience.

## Project Goals

This project aims to:
- Teach AI agent orchestration patterns (LangGraph + CrewAI, fully coupled)
- Provide a working HR resume screening agent for O'Reilly courses
- Demonstrate production-ready practices with Azure AI Foundry
- Remain beginner-friendly and well-documented

## 🤝 How to Contribute

### Types of Contributions Welcome

#### 📚 Documentation
- Fix typos or unclear explanations
- Add examples or clarifications
- Improve teaching guides
- Translate to other languages

#### 🐛 Bug Fixes
- Fix broken functionality
- Improve error handling
- Update deprecated dependencies

#### Features (Please Discuss First)
- New CrewAI agent types (beyond PolicyExpert, ResumeAnalyst, DecisionMaker)
- Additional tool integrations (beyond ChromaDB and Brave Search)
- New orchestration patterns
- Teaching aids (diagrams, exercises)

#### ❌ Not Accepting
- Major architecture changes (would break teaching flow)
- Features that complicate setup
- Non-educational additions

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR-USERNAME/agents2.git
cd agents2/contoso-hr-agent
```

### 2. Set Up Environment

```bash
# Install uv (if not already installed)
# See https://docs.astral.sh/uv/getting-started/installation/

# Install dependencies
uv sync

# Configure .env
cp .env.example .env
# Add your Azure AI Foundry and Brave Search API keys
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# OR
git checkout -b fix/issue-description
```

### 4. Make Changes

- Follow existing code style (see Code Standards below)
- Add tests if applicable
- Update documentation
- Keep commits focused and atomic

### 5. Test Your Changes

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=contoso_hr_agent

# Run the HR engine (port 8080)
uv run hr-engine

# Run the folder watcher
uv run hr-watcher

# Run the MCP server (port 8081)
uv run hr-mcp

# Seed the knowledge base
uv run hr-seed
```

### 6. Commit and Push

```bash
git add .
git commit -m "feat: add security agent example"
# Use conventional commits: feat, fix, docs, test, refactor

git push origin feature/your-feature-name
```

### 7. Open a Pull Request

- Go to the [Pull Requests page](https://github.com/timothywarner-org/agents2/pulls)
- Click "New Pull Request"
- Select your branch
- Fill out the PR template

## 📋 Pull Request Guidelines

### PR Checklist

- [ ] Branch is up-to-date with `main`
- [ ] Tests pass locally (`pytest`)
- [ ] Code follows style guidelines (see below)
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] PR description explains what/why

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring
- [ ] Teaching improvement

## Testing
How did you test this?

## Screenshots (if applicable)
Add screenshots for UI/output changes

## Related Issues
Closes #123
```

## 🎨 Code Standards

### Python Style

- **PEP 8** compliance
- **Line length:** 100 characters (configured in ruff)
- **Type hints:** Use where helpful (not required everywhere)
- **Docstrings:** Required for public functions

```python
def example_function(param: str) -> dict:
    """
    Brief description of what this does.

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
    return {"result": param}
```

### Project Structure

```
contoso-hr-agent/src/contoso_hr_agent/
├── __init__.py           # Package metadata only
├── models.py             # Pydantic models
├── config.py             # Configuration
├── pipeline/             # LangGraph + CrewAI orchestration
├── tools/                # Agent tools (ChromaDB, Brave Search)
├── knowledge/            # ChromaDB vector store and ingestion
├── mcp/                  # FastMCP 2 server
└── watcher/              # Folder watcher for event-driven processing
```

**Rules:**
- No business logic in `__init__.py`
- Keep prompts separate from orchestration
- Use Pydantic for all data models
- Avoid deep nesting (max 3 levels)
- All resumes follow `RESUME_*.txt` naming in `sample_resumes/`
- Knowledge base documents go in `sample_knowledge/` (`.pdf`, `.docx`, `.pptx`, `.md`)

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add cost tracking to pipeline
fix: handle missing GitHub token gracefully
docs: update Hour 3 teaching guide
test: add schema validation tests
refactor: simplify error handling in watcher
```

### Testing

- Write tests for new features
- Keep tests simple and focused
- Use descriptive test names
- Mock external API calls

```python
def test_policy_expert_returns_valid_output():
    """PolicyExpertAgent should return structured evaluation."""
    # Given
    resume_text = "Sample resume content..."

    # When
    result = policy_expert_node({"resume": resume_text})

    # Then
    assert "policy_evaluation" in result
    assert result["policy_evaluation"]["compliant"] is not None
```

## 📖 Documentation Guidelines

### Teaching Guides

Located in `docs/`:
- Use simple language (middle school reading level)
- Include exact file paths and line numbers
- Add "What to SAY" vs "What to DO" sections
- Provide time estimates
- Include troubleshooting tips

### README Updates

- Keep main README focused on course outline
- Put technical details in `oreilly-agent-mvp/README.md`
- Use mermaid diagrams for visual learners
- Add code examples with comments

### Code Comments

- Explain WHY, not WHAT
- Document non-obvious decisions
- Use TODO/FIXME for known issues
- Keep comments up-to-date with code

```python
# Use structured JSON to ensure reliable parsing
# Natural language responses would require brittle regex
pm_data = _extract_json(response.content)
```

## 🔍 Review Process

### What We Look For

✅ **Good:**
- Solves a real problem
- Well-tested
- Clear documentation
- Maintains simplicity
- Enhances learning

❌ **Needs Work:**
- Breaks existing functionality
- Lacks tests
- Complicates setup
- Missing documentation

### Timeline

- Initial review: Within 3 business days
- Feedback: Ongoing conversation
- Merge: When approved by maintainer

## 💬 Getting Help

### Questions?

- **Documentation:** Check `contoso-hr-agent/README.md` first
- **Issues:** [Search existing issues](https://github.com/timothywarner-org/agents2/issues)
- **Discussion:** [Open a discussion](https://github.com/timothywarner-org/agents2/discussions)
- **Email:** tim@techtrainertim.com (for complex questions)

### Stuck on Setup?

See [Troubleshooting Guide](contoso-hr-agent/README.md#troubleshooting)

## 🏆 Recognition

Contributors are recognized in:
- Pull request acknowledgments
- Release notes (for significant contributions)
- Optional mention in course materials

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions help thousands of learners understand AI agents better. Every typo fix, bug report, and feature makes this project more valuable.

**Tim Warner**
tim@techtrainertim.com
[TechTrainerTim.com](https://TechTrainerTim.com)

---

*Happy coding! 🚀*
