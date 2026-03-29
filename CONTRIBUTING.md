# Contributing to agents2

Thank you for your interest in contributing to this O'Reilly Live Learning project!

This repository demonstrates AI agent patterns for educational purposes. The **active project** is `contoso-hr-agent/`, a Contoso HR Agent that screens Microsoft Certified Trainer resumes using LangGraph, CrewAI, FastMCP 2, and Azure AI Foundry. The `oreilly-agent-mvp/` directory is a legacy reference project and should not be modified unless explicitly requested. We welcome contributions that improve the learning experience.

## Project Goals

This project aims to:

- Teach AI agent orchestration patterns (LangGraph + CrewAI, fully coupled)
- Demonstrate **parallel subagent execution** (fan-out / fan-in) as the core teaching demo
- Provide a working HR resume screening agent for O'Reilly courses
- Demonstrate production-ready practices with Azure AI Foundry
- Remain beginner-friendly and well-documented

## How to Contribute

### Types of Contributions Welcome

#### Documentation

- Fix typos or unclear explanations
- Add examples or clarifications
- Improve teaching guides (docs/hour-*-teaching-guide.md)
- Translate to other languages

#### Bug Fixes

- Fix broken functionality in `contoso-hr-agent/`
- Improve error handling
- Update deprecated dependencies

#### Features (Please Discuss First)

- New CrewAI agent types (beyond ChatConcierge, PolicyExpert, ResumeAnalyst, DecisionMaker)
- Additional tool integrations (beyond ChromaDB and Brave Search)
- New orchestration patterns (e.g., additional parallel branches)
- Teaching aids (diagrams, exercises)
- Web UI improvements (chat.html, candidates.html, runs.html)
- MCP server enhancements (new tools, resources, prompts)

#### Not Accepting

- Major architecture changes (would break teaching flow)
- Features that complicate setup
- Non-educational additions
- Changes to `oreilly-agent-mvp/` (legacy reference only)

## Getting Started

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

# First-time setup (creates venv, installs deps, seeds ChromaDB)
uv venv && uv sync && uv run hr-seed

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
- Only modify files in `contoso-hr-agent/` (not `oreilly-agent-mvp/`)

### 5. Test Your Changes

```bash
# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest --cov=contoso_hr

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Run the HR engine (port 8080)
uv run hr-engine

# Run the folder watcher
uv run hr-watcher

# Run the MCP server (port 8081)
uv run hr-mcp

# Re-seed the knowledge base
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

## Pull Request Guidelines

### PR Checklist

- [ ] Branch is up-to-date with `main`
- [ ] Tests pass locally (`uv run pytest tests/ -v`)
- [ ] Lint passes (`uv run ruff check src/ tests/`)
- [ ] Code follows style guidelines (see below)
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] PR description explains what/why
- [ ] No changes to `oreilly-agent-mvp/` (unless explicitly requested)

## Code Standards

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

```text
contoso-hr-agent/src/contoso_hr/
+-- __init__.py           # Package metadata only
+-- models.py             # Pydantic v2 models (full data model chain)
+-- config.py             # Config dataclass, Azure AI Foundry LLM/embeddings factory
+-- engine.py             # FastAPI: /api/chat, /api/upload, /api/candidates, etc.
+-- pipeline/             # LangGraph StateGraph + CrewAI agents (parallel pipeline)
+-- knowledge/            # ChromaDB vectorizer and retriever
+-- memory/               # SQLite store and LangGraph checkpoints
+-- mcp_server/           # FastMCP 2 server (SSE on port 8081)
+-- watcher/              # Folder watcher for event-driven processing
+-- util/                 # Port utilities
```

**Rules:**

- No business logic in `__init__.py`
- Keep prompts separate from orchestration (prompts.py vs agents.py)
- Use Pydantic v2 for all data models
- Avoid deep nesting (max 3 levels)
- One `Crew.kickoff()` per LangGraph node -- no nested orchestration
- All resumes follow `RESUME_*.txt` naming in `sample_resumes/`
- Knowledge base documents go in `sample_knowledge/` (`.pdf`, `.docx`, `.pptx`, `.md`)
- `data/` directories are runtime-only -- never commit their contents

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add cost tracking to pipeline
fix: handle missing Azure AI Foundry key gracefully
docs: update Hour 3 teaching guide
test: add schema validation tests
refactor: simplify error handling in watcher
```

### Testing

- Write tests for new features
- Keep tests simple and focused
- Use descriptive test names
- Mock external API calls (Azure AI Foundry, Brave Search)
- Use `tmp_path` fixtures; no live API calls in unit tests

```python
def test_resume_submission_validates_required_fields():
    """ResumeSubmission should reject missing candidate name."""
    # Given
    data = {"resume_text": "Sample resume content..."}

    # When / Then
    with pytest.raises(ValidationError):
        ResumeSubmission(**data)
```

## Documentation Guidelines

### Teaching Guides

Located in `docs/`:

- Use simple language (middle school reading level)
- Include exact file paths and line numbers
- Add "What to SAY" vs "What to DO" sections
- Provide time estimates
- Include troubleshooting tips
- Highlight the **parallel pipeline** as the key teaching demo
- Reference runs.html as the live visualization tool

### README Updates

- Keep main README focused on course outline
- Put technical details in `contoso-hr-agent/README.md`
- Use mermaid diagrams for visual learners
- Add code examples with comments

### Code Comments

- Explain WHY, not WHAT
- Document non-obvious decisions
- Use TODO/FIXME for known issues
- Keep comments up-to-date with code

## Review Process

### What We Look For

**Good:**

- Solves a real problem
- Well-tested
- Clear documentation
- Maintains simplicity
- Enhances learning
- Preserves the parallel pipeline demo

**Needs Work:**

- Breaks existing functionality
- Lacks tests
- Complicates setup
- Missing documentation
- Modifies legacy project without justification

### Timeline

- Initial review: Within 3 business days
- Feedback: Ongoing conversation
- Merge: When approved by maintainer

## Getting Help

### Questions?

- **Documentation:** Check `contoso-hr-agent/README.md` and `CLAUDE.md` first
- **Issues:** [Search existing issues](https://github.com/timothywarner-org/agents2/issues)
- **Discussion:** [Open a discussion](https://github.com/timothywarner-org/agents2/discussions)
- **Email:** [tim@techtrainertim.com](mailto:tim@techtrainertim.com) (for complex questions)

### Stuck on Setup?

See the troubleshooting section in `contoso-hr-agent/README.md`.

## Recognition

Contributors are recognized in:

- Pull request acknowledgments
- Release notes (for significant contributions)
- Optional mention in course materials

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Thank You

Your contributions help thousands of learners understand AI agents better. Every typo fix, bug report, and feature makes this project more valuable.

**Tim Warner**
[tim@techtrainertim.com](mailto:tim@techtrainertim.com)
[TechTrainerTim.com](https://TechTrainerTim.com)

---

*Happy coding!*
