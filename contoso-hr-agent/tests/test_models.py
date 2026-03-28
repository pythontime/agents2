"""
Unit tests for Contoso HR Agent data models (no LLM calls).
"""

import pytest
from pydantic import ValidationError

from contoso_hr.models import (
    CandidateEval,
    CandidateSummary,
    ChatMessage,
    EvaluationResult,
    HRDecision,
    PolicyContext,
    ResumeSubmission,
    UploadResponse,
)


class TestResumeSubmission:
    def test_defaults(self):
        s = ResumeSubmission(filename="test.txt", raw_text="Hello world")
        assert s.source == "incoming_folder"
        assert len(s.candidate_id) == 8
        assert s.session_id

    def test_upload_source(self):
        s = ResumeSubmission(filename="cv.txt", raw_text="content", source="upload")
        assert s.source == "upload"

    def test_invalid_source(self):
        with pytest.raises(ValidationError):
            ResumeSubmission(filename="x.txt", raw_text="y", source="fax_machine")


class TestCandidateEval:
    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            CandidateEval(
                skills_match_score=101,
                experience_score=50,
                culture_fit_notes="ok",
            )

    def test_score_bounds_negative(self):
        with pytest.raises(ValidationError):
            CandidateEval(
                skills_match_score=50,
                experience_score=-1,
                culture_fit_notes="ok",
            )

    def test_valid_eval(self):
        e = CandidateEval(
            skills_match_score=85,
            experience_score=70,
            culture_fit_notes="Good growth mindset",
            strengths=["Azure certified", "Led migrations"],
            red_flags=[],
        )
        assert e.skills_match_score == 85
        assert len(e.strengths) == 2
        assert e.recommended_role is None


class TestHRDecision:
    def test_valid_decisions(self):
        for decision in ("advance", "hold", "reject"):
            d = HRDecision(
                decision=decision,
                reasoning="Test reason",
                overall_score=75,
            )
            assert d.decision == decision

    def test_invalid_decision(self):
        with pytest.raises(ValidationError):
            HRDecision(decision="maybe", reasoning="hmm", overall_score=50)

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            HRDecision(decision="advance", reasoning="x", overall_score=101)


class TestPolicyContext:
    def test_defaults(self):
        pc = PolicyContext()
        assert pc.chunks == []
        assert pc.sources == []
        assert pc.query == ""

    def test_with_content(self):
        pc = PolicyContext(
            chunks=["Policy text here"],
            sources=["hr_policy_hiring.md"],
            query="hiring policy",
        )
        assert len(pc.chunks) == 1


class TestEvaluationResult:
    def test_decision_property(self):
        result = EvaluationResult(
            candidate_id="abc12345",
            run_id="run-001",
            filename="test.txt",
            timestamp_utc="2026-01-01T00:00:00Z",
            candidate_eval=CandidateEval(
                skills_match_score=80, experience_score=70, culture_fit_notes=""
            ),
            hr_decision=HRDecision(
                decision="advance", reasoning="Strong candidate", overall_score=75
            ),
        )
        assert result.decision == "advance"
        assert result.overall_score == 75


class TestCandidateSummary:
    def test_creation(self):
        s = CandidateSummary(
            candidate_id="abc12345",
            run_id="run-001",
            filename="alice.txt",
            candidate_name="Alice Zhang",
            decision="advance",
            overall_score=88,
            timestamp_utc="2026-01-01T00:00:00Z",
        )
        assert s.candidate_name == "Alice Zhang"
        assert s.duration_seconds is None


class TestChatModels:
    def test_chat_message(self):
        msg = ChatMessage(message="What is the hiring policy?")
        assert msg.message == "What is the hiring policy?"
        assert msg.session_id  # auto-generated

    def test_upload_response_defaults(self):
        r = UploadResponse(candidate_id="abc", filename="test.txt")
        assert r.status == "queued"
        assert "queued" in r.message.lower()
