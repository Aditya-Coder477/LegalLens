"""
tests/test_api.py
=================
Integration tests for LegalLens FastAPI REST API endpoints.
"""

from fastapi.testclient import TestClient
from pipeline.api.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["evidence_first"] is True
    assert data["corpus_authority"] == "SYNTHETIC"


def test_dashboard_endpoint():
    res = client.get("/api/v1/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["total_documents"] > 0
    assert len(data["recent_documents"]) > 0
    assert len(data["recent_activity"]) > 0


def test_documents_list_and_detail():
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) > 0

    first_id = docs[0]["document_id"]
    detail_res = client.get(f"/api/v1/documents/{first_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["document_id"] == first_id
    assert "hierarchy" in detail
    assert detail["synthetic"] is True


def test_document_chunks():
    res = client.get("/api/v1/documents/SYN-ACT-001/chunks")
    assert res.status_code == 200
    chunks = res.json()
    assert len(chunks) > 0
    assert chunks[0]["document_id"] == "SYN-ACT-001"


def test_document_upload_json():
    payload = {
        "title": "Master Services Agreement",
        "document_type": "Contract",
        "text_content": "Section 1. Term and Termination.\nEither party may terminate upon 30 days notice.\n\nSection 2. Confidentiality.\nAll proprietary information shall remain confidential.",
        "source_authority": "USER_DOCUMENT",
        "synthetic": False,
    }
    res = client.post("/api/v1/documents/upload-json", json=payload)
    assert res.status_code == 200
    doc = res.json()
    assert doc["title"] == "Master Services Agreement"
    assert doc["document_id"].startswith("USER-DOC-")
    assert doc["source_authority"] == "USER_DOCUMENT"


def test_retrieve_endpoint():
    payload = {"query": "commencement date of the act", "top_k": 3}
    res = client.post("/api/v1/retrieve", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["results"]) > 0
    assert data["results"][0]["chunk_id"] is not None


def test_ai_answer_endpoint():
    payload = {
        "query": "What are the rules regarding data retention?",
        "document_id": "SYN-ACT-001",
        "top_k": 3,
    }
    res = client.post("/api/v1/ai/answer", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["task_type"] == "LEGAL_QA"
    assert len(data["claims"]) > 0
    assert data["status"] in ("VERIFIED", "PARTIALLY_SUPPORTED", "LIMITED_EVIDENCE")


def test_ai_summarize_and_simplify():
    sum_res = client.post("/api/v1/ai/summarize", json={"document_id": "SYN-ACT-001"})
    assert sum_res.status_code == 200

    sim_res = client.post("/api/v1/ai/simplify", json={"text": "Any party failing to adhere shall be penalized."})
    assert sim_res.status_code == 200
    assert sim_res.json()["task_type"] == "SIMPLIFY"


def test_ai_clause_analysis_and_compare():
    cl_res = client.post(
        "/api/v1/ai/analyze-clause",
        json={"clause_text": "Licensee shall indemnify Licensor against third-party claims."},
    )
    assert cl_res.status_code == 200

    cmp_res = client.post(
        "/api/v1/ai/compare",
        json={"doc_a_text": "Notice is 30 days.", "doc_b_text": "Notice is 60 days."},
    )
    assert cmp_res.status_code == 200


def test_ai_obligations_and_deadlines():
    ob_res = client.post("/api/v1/ai/obligations", json={"document_id": "SYN-ACT-001"})
    assert ob_res.status_code == 200

    dl_res = client.post("/api/v1/ai/deadlines", json={"document_id": "SYN-ACT-001"})
    assert dl_res.status_code == 200


def test_sources_and_activity():
    src_res = client.get("/api/v1/sources")
    assert src_res.status_code == 200
    assert len(src_res.json()) >= 5

    act_res = client.get("/api/v1/activity")
    assert act_res.status_code == 200
    assert len(act_res.json()) > 0
