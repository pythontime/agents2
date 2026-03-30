# Pydantic v2 Models — Contoso HR Agent

Reference for `src/contoso_hr/models.py`.

---

## Model Chain

Every resume evaluation flows through this exact linear chain:

```
ResumeSubmission          ← Input from upload or watcher
      ↓
PolicyContext             ← ChromaDB retrieval result (injected at intake/policy_expert)
      ↓
CandidateEval             ← ResumeAnalyst + PolicyExpert outputs combined
      ↓
HRDecision                ← DecisionMaker output with final disposition
      ↓
EvaluationResult          ← Final persisted record (SQLite + API response)
```

**Never shortcut this chain.** Do not add evaluation scores to `ResumeSubmission`,
and do not add input metadata to `EvaluationResult`.

---

## Model Definitions

### ResumeSubmission — Input

```python
class ResumeSubmission(BaseModel):
    resume_text: str = Field(..., min_length=50, description="Full resume text")
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    source: Literal["upload", "watcher", "api"] = "api"
```

### PolicyContext — Retrieval Result

```python
class PolicyContext(BaseModel):
    chunks: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    query: str = ""
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def summary(self) -> str:
        """First 500 chars of first chunk, for task description injection."""
        return self.chunks[0][:500] if self.chunks else ""
```

### CandidateEval — Analyst Scores

```python
class CandidateEval(BaseModel):
    skills_match_score: float = Field(..., ge=0.0, le=100.0)
    experience_score: float = Field(..., ge=0.0, le=100.0)
    strengths: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    recommended_role: str = ""
    web_research_notes: str = ""
    culture_fit_notes: str = ""
```

### HRDecision — Final Disposition

```python
DISPOSITION = Literal["Strong Match", "Possible Match", "Needs Review", "Not Qualified"]

class HRDecision(BaseModel):
    decision: DISPOSITION                                    # ← ALWAYS use this type
    reasoning: str = Field(..., min_length=20)
    next_steps: list[str] = Field(default_factory=list)
    overall_score: float = Field(..., ge=0.0, le=100.0)
    policy_context_summary: str = ""
    compliance_notes: str = ""
    recommended_level: str = ""
    compensation_band: str = ""
```

### EvaluationResult — Persisted Record

```python
class EvaluationResult(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    run_id: str
    submitted_at: datetime
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    resume_text: str

    # From CandidateEval
    skills_match_score: float
    experience_score: float
    strengths: list[str]
    red_flags: list[str]
    recommended_role: str
    culture_fit_notes: str

    # From HRDecision
    decision: DISPOSITION                                    # ← ALWAYS use this type
    overall_score: float
    reasoning: str
    next_steps: list[str]
    policy_context_summary: str
    compliance_notes: str
    recommended_level: str
    compensation_band: str

    # Token tracking (optional)
    token_usage: Optional[PipelineTokens] = None
```

---

## Pydantic v2 Rules

### Use `model_dump()` — Not `.dict()`

```python
# ✅ CORRECT (Pydantic v2)
result_dict = evaluation.model_dump()
result_json = evaluation.model_dump_json()
result_json_pretty = evaluation.model_dump_json(indent=2)

# ❌ WRONG (Pydantic v1 — silently broken in some v2 contexts)
result_dict = evaluation.dict()
result_json = evaluation.json()
```

### Use `model_validate_json()` — Not `parse_raw()`

```python
# ✅ CORRECT (Pydantic v2)
result = EvaluationResult.model_validate_json(json_str)
result = EvaluationResult.model_validate(dict_data)

# ❌ WRONG (Pydantic v1)
result = EvaluationResult.parse_raw(json_str)
result = EvaluationResult.parse_obj(dict_data)
```

### Use `model_json_schema()` — Not `schema()`

```python
# ✅ CORRECT (Pydantic v2)
schema = EvaluationResult.model_json_schema()

# ❌ WRONG (Pydantic v1)
schema = EvaluationResult.schema()
```

---

## Disposition Literals

The four dispositions are defined as a `Literal` type alias:

```python
DISPOSITION = Literal["Strong Match", "Possible Match", "Needs Review", "Not Qualified"]
```

**Score thresholds** (defined in `prompts.py`, enforced by LLM instructions):

| Disposition | Score Range | Next Action |
|-------------|-------------|-------------|
| Strong Match | 80–100 | Immediate interview |
| Possible Match | 55–79 | Technical screen |
| Needs Review | 35–54 | Recruiter follow-up |
| Not Qualified | 0–34 | Decline |

### Adding a New Disposition

If you ever add or rename a disposition (rare — requires explicit request):
1. Update `DISPOSITION` Literal in `models.py`
2. Update all threshold descriptions in `prompts.py` (4 agent prompts)
3. Update the badge CSS in `web/candidates.html` (each disposition has a color class)
4. Update the test fixtures in `tests/` that use specific disposition strings
5. Update `README.md` disposition table

---

## Token Tracking Models

```python
class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class AgentTokens(BaseModel):
    agent_name: str
    usage: TokenUsage

class PipelineTokens(BaseModel):
    agents: list[AgentTokens] = Field(default_factory=list)
    pipeline_total: TokenUsage = Field(default_factory=TokenUsage)
```

Token tracking is **optional** — `EvaluationResult.token_usage` may be `None`.
Never fail a pipeline run because token tracking is unavailable.

---

## Field Validators (Pydantic v2 Style)

```python
from pydantic import field_validator, model_validator

class CandidateEval(BaseModel):
    skills_match_score: float
    experience_score: float

    @field_validator("skills_match_score", "experience_score")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        if not 0.0 <= v <= 100.0:
            raise ValueError(f"Score must be between 0 and 100, got {v}")
        return round(v, 2)
```

Use `@field_validator` (Pydantic v2) — not `@validator` (Pydantic v1).

---

## SQLite Serialization

`HRSQLiteStore` in `memory/sqlite_store.py` stores `EvaluationResult` as JSON in
a `TEXT` column. Pattern:

```python
# Storing
store.save_evaluation(result)
# Internally: cursor.execute("INSERT INTO ...", (result.model_dump_json(),))

# Retrieving
row = cursor.fetchone()
result = EvaluationResult.model_validate_json(row[0])
```

Never manually construct SQL strings with f-strings for user-provided data.
Always use parameterized queries:

```python
# ✅ CORRECT — parameterized
cursor.execute("SELECT * FROM evaluations WHERE candidate_id = ?", (candidate_id,))

# ❌ WRONG — SQL injection risk
cursor.execute(f"SELECT * FROM evaluations WHERE candidate_id = '{candidate_id}'")
```

---

## Common Pydantic Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| `.dict()` call | `PydanticUserError` in strict mode | Use `model_dump()` |
| `parse_raw()` call | `AttributeError` | Use `model_validate_json()` |
| `str` for disposition | Fails Literal validation at runtime | Use `DISPOSITION` type |
| Field added to wrong model | Data appears at wrong pipeline stage | Check model chain ownership |
| `@validator` instead of `@field_validator` | Deprecation warning, wrong signature | Use Pydantic v2 style |
| Missing `Optional` for new field | `ValidationError` when field absent | Wrap with `Optional[T] = None` |
