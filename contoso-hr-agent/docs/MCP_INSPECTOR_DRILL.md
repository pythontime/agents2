# MCP Inspector — Type-This-Here Drill

Second-monitor reference for running Contoso HR Agent tools interactively in the MCP Inspector.

**URL:** http://localhost:6374 (auto-opened by `.\scripts\start.ps1`)
**Transport:** `stdio`
**Command:** `uv`
**Args:** `run hr-mcp --stdio`
→ click **Connect**

If the Inspector tab didn't open, the start script also prints the URL. The MCP server itself is fronted by stdio here (not the SSE port 8091) so JSON-RPC owns stdout — see `CLAUDE.md` for the stdio gotcha.

---

## 1. List recent candidates (warm-up)

Left pane → **Tools** → `list_candidates` → **Run Tool**

| Field | Value |
|-------|-------|
| `limit` | `5` |
| `decision_filter` | *(leave blank)* |

Copy any `candidate_id` from the response — you will paste it into the next steps.

---

## 2. Fetch one candidate

**Tools** → `get_candidate`

| Field | Value |
|-------|-------|
| `candidate_id` | *(paste from step 1)* |

---

## 3. Filter by disposition

**Tools** → `list_candidates`

| Field | Value |
|-------|-------|
| `limit` | `10` |
| `decision_filter` | `Strong Match` |

Try again with `Possible Match`, `Needs Review`, `Not Qualified`.

---

## 4. Hit the knowledge base directly

**Tools** → `query_policy`

| Field | Value |
|-------|-------|
| `question` | `What are the minimum certifications for an Azure trainer hire?` |

Repeat with:

- `What does the EDI policy say about interview topics?`
- `What is the compensation band for a senior technical trainer?`
- `What is the policy on remote training delivery?`

---

## 5. Sampling demo (LLM-via-client) — MCP Primitive 4

**Tools** → `generate_eval_summary`

| Field | Value |
|-------|-------|
| `candidate_id` | *(same id from step 1)* |

The Inspector pops a **Sampling Request** modal — click **Approve**. The server calls back into the connected client's LLM and returns an executive briefing. This is the only path where the *server* drives an LLM call through the *client*.

---

## 6. Elicitation demo (user-confirm-in-loop) — MCP Primitive 5

**Tools** → `confirm_and_evaluate`

| Field | Value |
|-------|-------|
| `resume_text` | *(paste a few lines from `sample_resumes/RESUME_Alice_Zhang_Azure_Trainer-v1.txt`)* |
| `filename` | `alice_zhang_inspector.txt` |

The Inspector shows an **Elicitation** form mid-tool. Fill:

- `confirmed`: `true` (checkbox)
- `priority`: `normal` *(also valid: `urgent`, `low`)*

→ **Submit**. Pipeline runs ~30–60s and returns a full `EvaluationResult` dict.

Then refresh http://localhost:8090/candidates.html — the new submission appears live in the grid, closing the MCP-to-UI loop.

---

## 7. Resource templates (right pane → Resources)

Paste these URIs one at a time into the Resources panel:

| URI | What it returns |
|-----|-----------------|
| `candidate://{paste-id-from-step-1}` | Formatted markdown profile for that candidate |
| `policy://compensation` | ChromaDB semantic search over compensation policy |
| `policy://hiring` | ChromaDB semantic search over hiring policy |
| `policy://edi` | ChromaDB semantic search over EDI policy |
| `stats://evaluations` | Aggregate counts by disposition |
| `samples://resumes` | List of sample resume filenames |
| `schema://candidate` | JSON schema for the candidate record |
| `config://settings` | Non-secret server config |

---

## 8. Prompts (right pane → Prompts)

| Prompt | Args | Purpose |
|--------|------|---------|
| `evaluate_resume` | `resume_text`, `role_title` | Multi-message trainer eval template |
| `policy_query` | `question` | Structured policy Q&A template |
| `disposition_review` | `candidate_id` | Fetches candidate + formats for hiring-committee review (uses an embedded Context resource) |

---

## 9. Resource deep-dive (Resources panel)

These exercise both static resources and parameterized resource templates. All read-only, all sub-second, all safe to run mid-demo.

### 9a. Static resource — `config://settings`

Paste `config://settings` into the Resources panel. Confirms the server is talking to the right Azure deployment without exposing keys.

| Field to look for | Expected value |
|-------------------|----------------|
| `chat_model` | `gpt-5.4-1` |
| `embedding_model` | `text-embedding-ada-002-1` |
| `endpoint` | `https://scribe-foundry-resource.cognitiveservices.azure.com/` |
| `engine_port` | `8090` |
| `mcp_port` | `8091` |

If endpoint or models are wrong, your `.env` got out of sync — fix before continuing.

### 9b. Static resource — `samples://resumes`

Paste `samples://resumes`. Returns JSON listing every `RESUME_*.txt` in `sample_resumes/` with byte size. Use this to **discover** valid candidate fixtures live in the demo without leaving the Inspector.

### 9c. Static resource — `stats://evaluations`

Paste `stats://evaluations`. Returns aggregate counts by disposition (Strong Match / Possible Match / Needs Review / Not Qualified). Compare against the candidates grid at http://localhost:8090/candidates.html — numbers must match.

### 9d. Static resource — `schema://candidate`

Paste `schema://candidate`. Returns the full Pydantic v2 JSON Schema for `EvaluationResult`. Good for showing learners the **typed contract** the pipeline produces — every field, every constraint, the `Literal["Strong Match", ...]` for `decision`.

### 9e. Resource template — `policy://{topic}` (semantic search)

Paste each in turn — these hit ChromaDB and return the top 3 chunks with source attribution:

| URI | Demonstrates |
|-----|--------------|
| `policy://mct-requirements` | Lookup of trainer-specific qualification policy |
| `policy://learner-satisfaction` | Retrieval against satisfaction-rating policy |
| `policy://background-checks` | Multi-document chunk merge |
| `policy://nonexistent-flim-flam` | Graceful empty-result path (returns a "no content" message) |

### 9f. Resource template — `candidate://{id}` (markdown profile)

Paste `candidate://<id-from-step-1>`. Returns a fully formatted markdown profile (decision, scores, strengths, red flags, reasoning, next steps). The Inspector renders the markdown, so this is the **visually richest** resource — great closing flourish for the resources demo.

Also try `candidate://does-not-exist` — returns a graceful "Candidate Not Found" markdown card, not a crash.

---

## 10. Elicitation deep-dive — the three outcomes

The protocol defines three terminal states for an elicitation: **accept**, **decline**, **cancel**. The Inspector lets you exercise each one.

### 10a. Decline path

**Tools** → `confirm_and_evaluate`

| Field | Value |
|-------|-------|
| `resume_text` | `Brief test resume — will be declined` |
| `filename` | `decline_test.txt` |

When the elicitation form appears, set `confirmed`: `false` (uncheck), keep `priority`: `normal`, → **Submit**.

Expected response:

```json
{ "status": "declined", "message": "User chose not to proceed with evaluation." }
```

Pipeline never runs — proves elicitation is a true gate, not a notification.

### 10b. Cancel path

Run `confirm_and_evaluate` again with the same inputs. When the form appears, click the **X** / **Cancel** button instead of Submit.

Expected response:

```json
{ "status": "cancel", "message": "Evaluation cancelled — pipeline was not run." }
```

Distinct from decline — the user explicitly aborted rather than answering "no".

### 10c. Urgent-priority accept path

Run `confirm_and_evaluate` once more with a real resume snippet. In the form:

- `confirmed`: `true`
- `priority`: `urgent`

→ **Submit**. Pipeline runs. The `priority=urgent` value is echoed back into the server log via `ctx.info()` — open VS Code's **MCP: Show Output** view (or the terminal running `hr-mcp --stdio`) and you'll see the line `Evaluation confirmed (priority=urgent), starting pipeline...`. Demonstrates that elicitation data flows back into server-side logic, not just the response.

---

## 11. Sampling deep-dive — comparing LLM-written summaries

Sampling has one observable contract: **the server asks, the client's LLM writes**. Make that contract visible by running it on multiple candidates and contrasting the prose.

### 11a. Strong Match summary

Step 1 already gave you the list. Run `list_candidates` with `decision_filter`: `Strong Match`, copy that `candidate_id`, then:

**Tools** → `generate_eval_summary` → `candidate_id`: *(paste)*

Approve the Sampling Request modal. Output should lead with "Strong Match" and a numeric score ≥80, name the top strength, and recommend an interview as the next step.

### 11b. Not Qualified summary

Run `list_candidates` with `decision_filter`: `Not Qualified`. Copy that id, run `generate_eval_summary` again. Prose should change tone — leads with the disposition, surfaces a red flag, recommends a courtesy decline. **Same tool, same prompt template, radically different output because the input data is different**. That contrast is the teaching moment.

### 11c. Missing-candidate path

**Tools** → `generate_eval_summary`

| Field | Value |
|-------|-------|
| `candidate_id` | `deadbeef` |

Returns `"Candidate 'deadbeef' not found."` — the server short-circuits **before** calling `ctx.sample()`. Sampling Request modal never appears. Proves the server validates inputs and only consumes the client's LLM budget when it has real data to summarize.

### 11d. Token-budget observation

`generate_eval_summary` calls `ctx.sample(..., max_tokens=256)`. After running 11a and 11b, count words in each response — both should land at 3–5 sentences, well under the cap. If you ever see a response cut off mid-sentence, that's the cap biting; bump it in [server.py:273](contoso-hr-agent/src/contoso_hr/mcp_server/server.py#L273).

---

## Five MCP primitives covered

| # | Primitive | Demonstrated in step |
|---|-----------|----------------------|
| 1 | Resources (static) | 7 |
| 2 | Resource Templates (dynamic) | 7 |
| 3 | Tools | 1–4 |
| 4 | Sampling | 5 |
| 5 | Elicitation | 6 |

Prompts are the sixth feature (not always counted as a primitive) — step 8.

---

## If something is wrong

| Symptom | Fix |
|---------|-----|
| Inspector won't connect | `.\scripts\stop.ps1` then `.\scripts\start.ps1` — kills orphaned 5273/6374 procs |
| `SyntaxError: Unexpected number in JSON at position 2` | Something wrote to stdout in stdio mode — see `CLAUDE.md` "MCP stdio mode — DO NOT write to stdout" |
| `confirm_and_evaluate` hangs | The elicitation modal is hidden behind another window; alt-tab through Inspector tabs |
| Empty candidate list | Run `uv run python smoke_test.py` once to seed `hr.db` with Alice Zhang |
