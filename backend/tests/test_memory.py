"""
test_memory.py
--------------
Unit tests for Phase 7 — Memory Layer

Covers:
- LocalJSONSessionStore.save_session() persists records
- get_patient_history() filters by patient_id, sorted newest-first
- get_patient_history() with limit parameter
- get_recent_sessions() returns across all patients, sorted newest-first
- get_recent_sessions() respects limit
- Thread safety (concurrent saves)
- SessionStore abstract interface enforcement
- MemoryAgent integration with pipeline context
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import threading
import time
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta

from backend.memory.session_store import SessionStore
from backend.memory.patient_memory import LocalJSONSessionStore
from backend.agents.memory_agent.memory_agent import MemoryAgent
from backend.models.schemas import PipelineContext, EvaluationReport, RiskBreakdown


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_store(tmp_path):
    """Fresh LocalJSONSessionStore backed by a temp file for each test."""
    file_path = tmp_path / "sessions.json"
    return LocalJSONSessionStore(file_path=file_path)


def _session(patient_id="p1", timestamp_offset_seconds=0) -> dict:
    ts = (
        datetime.now(timezone.utc) + timedelta(seconds=timestamp_offset_seconds)
    ).isoformat()
    return {
        "patient_id": patient_id,
        "query": f"query for {patient_id}",
        "ai_response": "some AI response",
        "hallucinations": [],
        "risk_score": 0.5,
        "risk_level": "MODERATE",
        "safe_response": "safe response text",
        "timestamp": ts,
    }


# ===========================================================================
# SessionStore Abstract Interface
# ===========================================================================

class TestSessionStoreInterface:

    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            SessionStore()

    def test_local_json_store_implements_interface(self, tmp_store):
        assert isinstance(tmp_store, SessionStore)

    def test_interface_has_required_methods(self):
        for method in ["save_session", "get_patient_history", "get_recent_sessions"]:
            assert hasattr(SessionStore, method)


# ===========================================================================
# LocalJSONSessionStore — File Lifecycle
# ===========================================================================

class TestLocalJSONSessionStoreFile:

    def test_file_created_on_init(self, tmp_path):
        file_path = tmp_path / "new_sessions.json"
        assert not file_path.exists()
        LocalJSONSessionStore(file_path=file_path)
        assert file_path.exists()

    def test_file_contains_valid_json_array(self, tmp_path):
        file_path = tmp_path / "sessions.json"
        LocalJSONSessionStore(file_path=file_path)
        data = json.loads(file_path.read_text())
        assert isinstance(data, list)

    def test_missing_parent_dir_created(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c" / "sessions.json"
        store = LocalJSONSessionStore(file_path=nested)
        assert nested.parent.exists()


# ===========================================================================
# LocalJSONSessionStore — save_session
# ===========================================================================

class TestSaveSession:

    def test_returns_session_id_string(self, tmp_store):
        sid = tmp_store.save_session(_session())
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_session_persisted_to_file(self, tmp_store):
        tmp_store.save_session(_session("p1"))
        # Read directly from the underlying file path
        data = json.loads(tmp_store._file_path.read_text())
        assert len(data) == 1
        assert data[0]["patient_id"] == "p1"

    def test_multiple_sessions_appended(self, tmp_store):
        tmp_store.save_session(_session("p1"))
        tmp_store.save_session(_session("p2"))
        tmp_store.save_session(_session("p1"))
        data = json.loads(tmp_store._file_path.read_text())
        assert len(data) == 3

    def test_session_id_injected_into_record(self, tmp_store):
        sid = tmp_store.save_session(_session("p1"))
        data = json.loads(tmp_store._file_path.read_text())
        assert data[0]["session_id"] == sid

    def test_timestamp_auto_assigned_if_missing(self, tmp_store):
        record = {"patient_id": "p1", "query": "q", "ai_response": "a",
                  "hallucinations": [], "risk_score": 0.1, "risk_level": "LOW",
                  "safe_response": "safe"}
        tmp_store.save_session(record)
        data = json.loads(tmp_store._file_path.read_text())
        assert "timestamp" in data[0]

    def test_custom_session_id_respected(self, tmp_store):
        record = _session("p1")
        record["session_id"] = "my-custom-id-123"
        sid = tmp_store.save_session(record)
        assert sid == "my-custom-id-123"


# ===========================================================================
# LocalJSONSessionStore — get_patient_history
# ===========================================================================

class TestGetPatientHistory:

    def test_returns_only_matching_patient(self, tmp_store):
        tmp_store.save_session(_session("p1"))
        tmp_store.save_session(_session("p2"))
        tmp_store.save_session(_session("p1"))
        history = tmp_store.get_patient_history("p1")
        assert len(history) == 2
        assert all(s["patient_id"] == "p1" for s in history)

    def test_returns_empty_for_unknown_patient(self, tmp_store):
        tmp_store.save_session(_session("p1"))
        history = tmp_store.get_patient_history("unknown_patient")
        assert history == []

    def test_sorted_newest_first(self, tmp_store):
        tmp_store.save_session(_session("p1", timestamp_offset_seconds=0))
        time.sleep(0.01)
        tmp_store.save_session(_session("p1", timestamp_offset_seconds=10))
        history = tmp_store.get_patient_history("p1")
        # Newest first
        assert history[0]["timestamp"] > history[1]["timestamp"]

    def test_limit_parameter_respected(self, tmp_store):
        for i in range(5):
            tmp_store.save_session(_session("p1", timestamp_offset_seconds=i))
        history = tmp_store.get_patient_history("p1", limit=3)
        assert len(history) == 3

    def test_limit_none_returns_all(self, tmp_store):
        for i in range(4):
            tmp_store.save_session(_session("p1", timestamp_offset_seconds=i))
        history = tmp_store.get_patient_history("p1", limit=None)
        assert len(history) == 4


# ===========================================================================
# LocalJSONSessionStore — get_recent_sessions
# ===========================================================================

class TestGetRecentSessions:

    def test_returns_all_patients_sessions(self, tmp_store):
        tmp_store.save_session(_session("p1"))
        tmp_store.save_session(_session("p2"))
        tmp_store.save_session(_session("p3"))
        recent = tmp_store.get_recent_sessions(limit=10)
        patients = {s["patient_id"] for s in recent}
        assert "p1" in patients
        assert "p2" in patients
        assert "p3" in patients

    def test_sorted_newest_first(self, tmp_store):
        for i in range(3):
            time.sleep(0.01)
            tmp_store.save_session(_session("p1", timestamp_offset_seconds=i))
        recent = tmp_store.get_recent_sessions(limit=10)
        timestamps = [s["timestamp"] for s in recent]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_limit_respected(self, tmp_store):
        for i in range(8):
            tmp_store.save_session(_session("p1"))
        recent = tmp_store.get_recent_sessions(limit=5)
        assert len(recent) == 5

    def test_default_limit_is_10(self, tmp_store):
        for i in range(15):
            tmp_store.save_session(_session("p1"))
        recent = tmp_store.get_recent_sessions()
        assert len(recent) == 10


# ===========================================================================
# Thread Safety
# ===========================================================================

class TestThreadSafety:

    def test_concurrent_saves_no_data_loss(self, tmp_store):
        results = []
        errors = []

        def save_worker(i):
            try:
                sid = tmp_store.save_session(_session(f"patient_{i}"))
                results.append(sid)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=save_worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent saves: {errors}"
        data = json.loads(tmp_store._file_path.read_text())
        assert len(data) == 20


# ===========================================================================
# MemoryAgent Integration
# ===========================================================================

def _make_pipeline_context(patient_id="p1"):
    ctx = PipelineContext(
        patient_id=patient_id,
        query="test query",
        ai_response="original AI response",
        risk_score=0.75,
        risk_level="HIGH",
        safe_response="Safe medical guidance here.",
    )
    ctx.metadata["message_history"] = []
    return ctx


class TestMemoryAgentIntegration:

    def test_memory_saved_flag_set_on_success(self, tmp_path):
        store = LocalJSONSessionStore(file_path=tmp_path / "sessions.json")
        agent = MemoryAgent(store=store)
        ctx = _make_pipeline_context()
        result = agent.process(ctx)
        assert result.metadata.get("memory_saved") is True

    def test_session_id_stored_in_metadata(self, tmp_path):
        store = LocalJSONSessionStore(file_path=tmp_path / "sessions.json")
        agent = MemoryAgent(store=store)
        ctx = _make_pipeline_context()
        result = agent.process(ctx)
        assert "session_id" in result.metadata
        assert isinstance(result.metadata["session_id"], str)

    def test_session_persisted_with_correct_patient_id(self, tmp_path):
        store = LocalJSONSessionStore(file_path=tmp_path / "sessions.json")
        agent = MemoryAgent(store=store)
        ctx = _make_pipeline_context(patient_id="patient_abc")
        agent.process(ctx)
        history = store.get_patient_history("patient_abc")
        assert len(history) == 1
        assert history[0]["patient_id"] == "patient_abc"

    def test_session_stores_risk_score(self, tmp_path):
        store = LocalJSONSessionStore(file_path=tmp_path / "sessions.json")
        agent = MemoryAgent(store=store)
        ctx = _make_pipeline_context()
        ctx.risk_score = 0.92
        agent.process(ctx)
        history = store.get_recent_sessions(limit=1)
        assert history[0]["risk_score"] == pytest.approx(0.92)

    def test_session_stores_safe_response(self, tmp_path):
        store = LocalJSONSessionStore(file_path=tmp_path / "sessions.json")
        agent = MemoryAgent(store=store)
        ctx = _make_pipeline_context()
        ctx.safe_response = "This is the safe response."
        agent.process(ctx)
        history = store.get_recent_sessions(limit=1)
        assert history[0]["safe_response"] == "This is the safe response."

    def test_evaluation_report_stored(self, tmp_path):
        store = LocalJSONSessionStore(file_path=tmp_path / "sessions.json")
        agent = MemoryAgent(store=store)
        ctx = _make_pipeline_context()
        ctx.evaluation_report = EvaluationReport(
            coverage_score=90.0,
            consistency_score=85.0,
            risk_consistency_score=95.0,
            safety_score=88.0,
            overall_score=89.5,
            passed=True,
        )
        agent.process(ctx)
        history = store.get_recent_sessions(limit=1)
        assert history[0]["evaluation"] is not None
        assert history[0]["evaluation"]["passed"] is True

    def test_trace_added_by_memory_agent(self, tmp_path):
        store = LocalJSONSessionStore(file_path=tmp_path / "sessions.json")
        agent = MemoryAgent(store=store)
        ctx = _make_pipeline_context()
        result = agent.process(ctx)
        trace_names = [t.agent_name for t in result.traces]
        assert "MemoryAgent" in trace_names

    def test_a2a_message_sent_to_alert_agent(self, tmp_path):
        store = LocalJSONSessionStore(file_path=tmp_path / "sessions.json")
        agent = MemoryAgent(store=store)
        ctx = _make_pipeline_context()
        result = agent.process(ctx)
        receivers = [m["receiver"] for m in result.metadata.get("message_history", [])]
        assert "AlertAgent" in receivers

    def test_multiple_sessions_same_patient(self, tmp_path):
        store = LocalJSONSessionStore(file_path=tmp_path / "sessions.json")
        agent = MemoryAgent(store=store)
        for _ in range(3):
            ctx = _make_pipeline_context(patient_id="p_repeat")
            agent.process(ctx)
        history = store.get_patient_history("p_repeat")
        assert len(history) == 3
