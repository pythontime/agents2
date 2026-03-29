# Support

Welcome! This document helps you get support for the **agents2** project.

**Active project:** `contoso-hr-agent/` (Contoso HR Agent for MCT resume screening).
The `oreilly-agent-mvp/` directory is a legacy reference project and is not actively maintained.

## Documentation First

Before asking for help, check these resources:

### Quick Links

- **[Main README](README.md)** -- Course outline and prerequisites
- **[Technical README](contoso-hr-agent/README.md)** -- Setup, architecture, and troubleshooting
- **[CLAUDE.md](CLAUDE.md)** -- Full architecture reference (pipeline, agents, data models)
- **[Teaching Guides](docs/)** -- Hour-by-hour instructions
- **[Troubleshooting](contoso-hr-agent/README.md#troubleshooting)** -- Common issues and fixes

### Video Tutorials

- Check [TechTrainerTim.com](https://TechTrainerTim.com) for video walkthroughs
- O'Reilly Live Learning session recordings (if enrolled)

## Found a Bug?

### Before Reporting

1. **Update to latest:** `git pull origin main`
2. **Check existing issues:** [Search here](https://github.com/timothywarner-org/agents2/issues)
3. **Reproduce:** Can you make it happen twice?

### Reporting a Bug

[Create a new issue](https://github.com/timothywarner-org/agents2/issues/new?template=bug_report.md) using the bug report template.

**Include:** Description, steps to reproduce, environment details, and the full error message.

## Have a Question?

### For Setup/Installation Issues

**Check:**

- [Setup instructions](contoso-hr-agent/README.md#quick-start-before-class)
- [Troubleshooting section](contoso-hr-agent/README.md#troubleshooting)
- [Environment configuration](contoso-hr-agent/README.md#configuration)

**Common Issues:**

- Python version too old: Requires 3.11+
- API keys not working: Check `.env` format (Azure AI Foundry endpoint, key, model names)
- Missing `uv`: Install from <https://docs.astral.sh/uv/getting-started/installation/>
- Import errors: Run commands with `uv run` to use the managed environment
- ChromaDB issues: Re-seed with `uv run hr-seed`
- Port conflicts: The engine (8080) and MCP server (8081) auto-kill conflicting processes on startup

**Still stuck?** [Open a discussion](https://github.com/timothywarner-org/agents2/discussions)

---

### For Usage Questions

**Example questions:**

- "How do I add a new CrewAI agent to the parallel pipeline?"
- "Can I use a different LLM provider instead of Azure AI Foundry?"
- "How do I add custom knowledge documents for resume screening?"
- "How does the fan-out/fan-in pattern work in graph.py?"

**Best place:** [GitHub Discussions](https://github.com/timothywarner-org/agents2/discussions)

**Include:**

- What you're trying to do
- What you've tried so far
- Relevant code snippets

---

### For Course-Related Questions

**If you're enrolled in the O'Reilly course:**

- Use the course Q&A platform
- Ask during live session
- Check course discussion forums

**Not enrolled?** The code is open source, but course-specific content is for enrollees.

---

### For Teaching/Training Inquiries

**Want to use this in your course?**

- This project is MIT licensed -- use freely!
- Credit appreciated but not required
- [Email Tim](mailto:tim@techtrainertim.com) if you'd like teaching tips

---

## Feature Requests

Have an idea for improvement?

### Good Feature Requests

- Solve a real problem
- Fit the educational mission
- Are feasible to implement
- Maintain simplicity
- Apply to `contoso-hr-agent/` (the active project)

### How to Request

[Open a discussion](https://github.com/timothywarner-org/agents2/discussions) with:

- Problem you're solving
- Proposed solution
- Why it helps learners
- Alternative approaches considered

**Note:** This is an educational project. Features that complicate setup or confuse learners may not be accepted.

---

## Security Issues

**Found a security vulnerability?**

- **DO NOT** open a public issue
- **DO** email [tim@techtrainertim.com](mailto:tim@techtrainertim.com) with subject: [SECURITY]
- See [SECURITY.md](SECURITY.md) for details

---

## Contributing

Want to help improve the project?

- Read [CONTRIBUTING.md](CONTRIBUTING.md)
- Check [Good First Issues](https://github.com/timothywarner-org/agents2/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
- Fix documentation typos
- Add examples or clarifications

---

## Direct Contact

### When to Email

Email [tim@techtrainertim.com](mailto:tim@techtrainertim.com) for:

- Security issues (see SECURITY.md)
- Speaking/training inquiries
- Press/media requests
- Private concerns

### When NOT to Email

Don't email for:

- Bug reports (use GitHub Issues)
- General questions (use Discussions)
- Setup help (use Troubleshooting docs)
- Feature requests (use Discussions)

**Response time:** Usually within 3 business days

---

## Community Resources

### Official Channels

- **GitHub:** [timothywarner-org/agents2](https://github.com/timothywarner-org/agents2)
- **Website:** [TechTrainerTim.com](https://TechTrainerTim.com)
- **Email:** [tim@techtrainertim.com](mailto:tim@techtrainertim.com)

### Related Communities

- **LangChain Discord:** [Invite link](https://discord.gg/langchain)
- **CrewAI GitHub:** [crewaiinc/crewai](https://github.com/crewaiinc/crewai)
- **Reddit:** r/LangChain, r/ChatGPT

**Note:** These are external communities not managed by this project.

---

## Support Priority

### High Priority (24-48 hours)

- Security vulnerabilities
- Setup blockers for course participants
- Data loss or corruption issues

### Normal Priority (3-5 business days)

- Bug reports
- Documentation issues
- Feature discussions

### Low Priority (Best effort)

- Enhancement requests
- "Nice to have" features
- Non-critical improvements

---

## Course Participants

### During Live Sessions

- Ask questions in chat
- Use raise hand feature
- Participate in Q&A segments

### After Sessions

- Course discussion forums
- Office hours (if offered)
- GitHub Discussions for code issues

### Certification/Completion

- Contact O'Reilly Media support
- Not handled through this GitHub repo

---

## Thank You

Thanks for using this project for learning! Your questions and feedback help improve the course for everyone.

**Remember:**

- Be patient -- we're all learning
- Be kind -- everyone starts somewhere
- Be specific -- details help us help you
- Be grateful -- this is open source and free

---

**Tim Warner**
Instructor, O'Reilly Live Learning
[tim@techtrainertim.com](mailto:tim@techtrainertim.com)
[TechTrainerTim.com](https://TechTrainerTim.com)

Last updated: March 2026
