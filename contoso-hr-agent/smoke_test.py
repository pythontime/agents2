"""One-shot end-to-end pipeline acceptance test.

Submits the Alice Zhang fixture (canonical Strong Match — Azure MCT with the
cert stack the rubric rewards) through the full LangGraph pipeline and asserts:
  - disposition == "Strong Match"
  - overall_score >= 80

Reads the resume into memory and submits the TEXT (not the file path) to
process_resume_text. This is critical: process_resume_file would move the
source file to data/processed/, removing it from sample_resumes/. The text
pathway leaves sample_resumes/ untouched so this script is idempotent.

Exit codes:
    0  PASS — disposition + score gates met
    2  fixture file missing
    3  pipeline returned None
    4  disposition mismatch (rubric / prompts / model deployment drifted)
    5  overall_score below threshold

Costs real Azure (gpt-5.4-1 + text-embedding-ada-002-1) and Brave Search
API calls. Run before any live delivery; not free, not offline.

Run from contoso-hr-agent/:
    uv run python smoke_test.py
"""

import sys
import time
from pathlib import Path

from contoso_hr.watcher.process_resume import process_resume_text

resume = Path("sample_resumes/RESUME_Alice_Zhang_Azure_Trainer-v1.txt")
if not resume.exists():
    print(f"FAIL: {resume} not found")
    sys.exit(2)

print(f"Submitting: {resume.name}")
raw_text = resume.read_text(encoding="utf-8")
t0 = time.time()
result = process_resume_text(raw_text, resume.name, source_path=None)
elapsed = time.time() - t0

if result is None:
    print(f"FAIL: pipeline returned None after {elapsed:.1f}s")
    sys.exit(3)

print(f"Pipeline elapsed: {elapsed:.1f}s")
print(f"Candidate ID: {result.candidate_id}")
print(f"Candidate name: {result.candidate_name}")
print(f"Disposition: {result.hr_decision.decision}")
print(f"Overall score: {result.hr_decision.overall_score}")
print(f"Skills score: {result.candidate_eval.skills_match_score}")
print(f"Experience score: {result.candidate_eval.experience_score}")
print(f"Strengths (first 2): {result.candidate_eval.strengths[:2]}")
print(f"Reasoning (first 200 chars): {result.hr_decision.reasoning[:200]}")

# Acceptance gate: Alice is the canonical Strong Match fixture. If the model
# stops agreeing, the rubric, prompts, or model deployment have drifted —
# catch it here before a live O'Reilly delivery, not on stage.
EXPECTED_DISPOSITION = "Strong Match"
MIN_OVERALL_SCORE = 80

if result.hr_decision.decision != EXPECTED_DISPOSITION:
    print(f"\nFAIL: expected disposition {EXPECTED_DISPOSITION!r}, got {result.hr_decision.decision!r}")
    sys.exit(4)
if result.hr_decision.overall_score < MIN_OVERALL_SCORE:
    print(f"\nFAIL: expected overall_score >= {MIN_OVERALL_SCORE}, got {result.hr_decision.overall_score}")
    sys.exit(5)

print(f"\nPASS: {EXPECTED_DISPOSITION} with score {result.hr_decision.overall_score} >= {MIN_OVERALL_SCORE}")
