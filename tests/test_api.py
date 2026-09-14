import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    """Verify health endpoint returns ok, database backend, and chunk counts."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "active_provider" in data
    assert data["indexed_chunks"] > 0
    assert data["episodes_indexed"] >= 15
    assert data["database_backend"] in ["PostgreSQL", "SQLite"]

def test_session_lifecycle():
    """Verify session creation, listing, detail retrieval, and deletion."""
    # 1. Create session
    create_res = client.post("/api/sessions", json={"title": "Test PM Strategy Session"})
    assert create_res.status_code == 200
    session_data = create_res.json()
    session_id = session_data["id"]
    assert session_data["title"] == "Test PM Strategy Session"

    # 2. List sessions
    list_res = client.get("/api/sessions")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert any(s["id"] == session_id for s in sessions)

    # 3. Get session detail
    detail_res = client.get(f"/api/sessions/{session_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == session_id
    assert len(detail["messages"]) == 0

    # 4. Delete session
    del_res = client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 204

    # 5. Verify 404 on deleted session
    get_del = client.get(f"/api/sessions/{session_id}")
    assert get_del.status_code == 404

def test_grounded_chat_with_sources():
    """Verify grounded answer and citation generation for a known topic."""
    payload = {
        "message": "What did Elena Verna say about B2B growth tactics that never work?",
        "provider": "mock"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["is_grounded"] is True
    assert "Elena Verna" in data["answer"]
    assert len(data["sources"]) > 0

    # Inspect citations
    first_source = data["sources"][0]
    assert first_source["speaker"] != ""
    assert "Elena Verna" in first_source["speaker"] or "Elena" in first_source["episode_title"]
    assert ":" in first_source["timestamp_range"]
    assert first_source["relevance_score"] > 0.3

    # Verify session was created and contains messages
    session_id = data["session_id"]
    detail_res = client.get(f"/api/sessions/{session_id}")
    assert detail_res.status_code == 200
    messages = detail_res.json()["messages"]
    assert len(messages) == 2  # user + assistant
    assert messages[1]["sources_cited"] is not None

def test_ungrounded_query_declines_guessing():
    """Verify that an out-of-domain query is flagged ungrounded and refuses to fabricate."""
    payload = {
        "message": "How do I make chocolate chip cookies at 350 degrees?",
        "provider": "mock"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["is_grounded"] is False
    assert len(data["sources"]) == 0
    assert "could not find" in data["answer"].lower() or "indexed episodes" in data["answer"].lower()

def test_ship30_skill_transformation():
    """Verify that the Ship 30 for 30 skill produces a formatted essay with rubric adherence."""
    # First ask a question
    chat_res = client.post("/api/chat", json={
        "message": "Explain Brian Balfour's Four Fits growth framework",
        "provider": "mock"
    })
    assert chat_res.status_code == 200
    chat_data = chat_res.json()

    # Transform into Ship 30 for 30 essay
    ship_res = client.post("/api/chat/ship30", json={
        "session_id": chat_data["session_id"],
        "message_id": chat_data["message_id"],
        "topic": "The Four Fits Framework for Product-Led Growth",
        "provider": "mock"
    })
    assert ship_res.status_code == 200
    essay_data = ship_res.json()

    assert essay_data["word_count"] >= 500
    assert "# " in essay_data["essay_markdown"]
    assert "Tomorrow at 9 AM" in essay_data["essay_markdown"] or "Protocol" in essay_data["essay_markdown"]
    assert "<html" in essay_data["essay_html"]
    assert "sandbox" not in essay_data["essay_html"].lower() or "iframe" not in essay_data["essay_html"].lower()  # pure styled html
    assert essay_data["core_takeaway"] != ""

def test_ollama_graceful_error_when_offline():
    """Verify that if Ollama is requested when offline, backend returns a structured 503 rather than crashing."""
    payload = {
        "message": "What did Shreyas Doshi say about high-agency PMs?",
        "provider": "ollama"
    }
    response = client.post("/api/chat", json=payload)
    # If Ollama happens to run locally, it returns 200; if not, it returns 503 with structured JSON error
    if response.status_code == 503:
        err = response.json()
        assert "detail" in err
        assert "OLLAMA" in err["detail"].get("code", "")
        assert "troubleshooting" in err["detail"]
    else:
        assert response.status_code == 200
