import asyncio
import os
import sys
import time
from types import SimpleNamespace

from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import api.main as api_main
from src.state import Ask, Result


def _make_complete_result(text: str) -> Result:
    return Result(
        user_input=text,
        query=text,
        status="complete",
        message=None,
        user_response="ok",
    )


def _make_incomplete_result(text: str) -> Result:
    return Result(
        user_input=text,
        query=text,
        status="incomplete",
        message="지역, 학력 정보를 알려주세요.",
        missing_fields=["지역", "학력"],
    )


def _make_graph(
    chunks: list[dict[str, dict[str, object]]],
    error: str | None = None,
    delay: float = 0.0,
):
    def stream(_state, stream_mode="updates"):
        if stream_mode != "updates":
            raise AssertionError("stream_mode must be updates")

        idx = 0
        while idx < len(chunks):
            if delay > 0:
                time.sleep(delay)
            yield chunks[idx]
            idx += 1

        if error is not None:
            raise RuntimeError(error)

    return SimpleNamespace(stream=stream)


def test_health_and_query_sync(monkeypatch):
    async def fake_run(body: Ask) -> Result:
        return _make_complete_result(body.user_input)

    monkeypatch.setattr(api_main, "_run_query_request", fake_run)

    with TestClient(api_main.app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

        res = client.post("/query", json={"user_input": "테스트"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "complete"
        assert data["user_input"] == "테스트"
        assert data["query"] == "테스트"


def test_query_jobs_done(monkeypatch):
    async def fake_run(_job_id: str, user_input: str) -> Result:
        await asyncio.sleep(0.02)
        return _make_complete_result(user_input)

    monkeypatch.setattr(api_main, "_run_query_job", fake_run)

    with TestClient(api_main.app) as client:
        res = client.post("/query/jobs", json={"user_input": "서울 백엔드"})
        assert res.status_code == 202
        accepted = res.json()
        assert accepted["status"] == "queued"
        assert accepted["step"] == "queued"
        assert accepted["step_label"] == "대기열 처리 중"
        assert isinstance(accepted["job_id"], str)
        assert accepted["job_id"]
        assert isinstance(accepted["jobId"], str)
        assert accepted["jobId"]
        assert accepted["job_id"] == accepted["jobId"]

        job_id = accepted["job_id"]

        done = None
        count = 0
        while count < 100:
            poll = client.get(f"/query/jobs/{job_id}")
            assert poll.status_code == 200
            payload = poll.json()
            if payload["status"] == "done":
                done = payload
                break
            time.sleep(0.02)
            count += 1

        assert done is not None
        assert done["job_id"] == job_id
        assert done["jobId"] == job_id
        assert done["result"]["status"] == "complete"
        assert done["result"]["user_input"] == "서울 백엔드"


def test_query_jobs_failed(monkeypatch):
    async def fake_run(_job_id: str, _user_input: str) -> Result:
        raise RuntimeError("boom")

    monkeypatch.setattr(api_main, "_run_query_job", fake_run)

    with TestClient(api_main.app) as client:
        res = client.post("/query/jobs", json={"user_input": "실패 케이스"})
        assert res.status_code == 202
        body = res.json()
        job_id = body["job_id"]
        assert body["jobId"] == job_id

        failed = None
        count = 0
        while count < 100:
            poll = client.get(f"/query/jobs/{job_id}")
            assert poll.status_code == 200
            payload = poll.json()
            if payload["status"] == "failed":
                failed = payload
                break
            time.sleep(0.02)
            count += 1

        assert failed is not None
        assert failed["job_id"] == job_id
        assert failed["jobId"] == job_id
        assert "boom" in failed["message"]


def test_query_jobs_not_found():
    with TestClient(api_main.app) as client:
        res = client.get("/query/jobs/not-found")
        assert res.status_code == 404
        assert res.json() == {"message": "job not found"}


def test_query_jobs_ttl_cleanup(monkeypatch):
    monkeypatch.setenv("JOB_RESULT_TTL_SECONDS", "1")
    monkeypatch.setenv("JOB_CLEANUP_INTERVAL_SECONDS", "1")

    async def fake_run(_job_id: str, user_input: str) -> Result:
        return _make_complete_result(user_input)

    monkeypatch.setattr(api_main, "_run_query_job", fake_run)

    with TestClient(api_main.app) as client:
        res = client.post("/query/jobs", json={"user_input": "TTL 테스트"})
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        count = 0
        while count < 100:
            poll = client.get(f"/query/jobs/{job_id}")
            assert poll.status_code == 200
            if poll.json()["status"] == "done":
                break
            time.sleep(0.02)
            count += 1

        time.sleep(2.2)

        not_expired = client.get(f"/query/jobs/{job_id}")
        assert not_expired.status_code == 200
        assert not_expired.json()["status"] == "done"

        api_main.job_store[job_id]["updated_at"] = time.time() - 301
        time.sleep(1.2)

        expired = client.get(f"/query/jobs/{job_id}")
        assert expired.status_code == 404
        assert expired.json() == {"message": "job not found"}


def test_query_jobs_running_step_transition(monkeypatch):
    from src import graph as graph_module

    chunks = [
        {
            "normalize_entities": {
                "status": "complete",
                "message": None,
                "missing_fields": None,
                "normalized_entities": {
                    "지역": "서울",
                    "직무": "백엔드/서버개발",
                    "경력": "신입",
                    "학력": "4년제대학교",
                },
            }
        },
        {"map_url": {"url": "https://example.com/jobs"}},
        {"crawl_html": {"crawled_count": 2}},
        {"parse_job_info": {"job_info_list": ["공고A", "공고B"]}},
        {"search_hybrid": {"retrieved_job_info_list": ["공고A"], "retrieved_scores": [0.91]}},
        {"generate_user_response": {"user_response": "추천 결과"}},
    ]

    monkeypatch.setattr(graph_module, "get_compiled_graph", lambda: _make_graph(chunks, delay=0.05))

    with TestClient(api_main.app) as client:
        res = client.post("/query/jobs", json={"user_input": "서울 백엔드 신입 대졸"})
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        steps = []
        done = None
        count = 0
        while count < 200:
            poll = client.get(f"/query/jobs/{job_id}")
            assert poll.status_code == 200
            payload = poll.json()
            if payload["status"] == "running":
                if payload["step"] is not None:
                    steps.append(payload["step"])
                if payload["step"] == "collecting":
                    assert payload["step_label"] == "공고 수집 중"
            if payload["status"] == "done":
                done = payload
                break
            time.sleep(0.02)
            count += 1

        assert done is not None
        assert "analyzing" in steps
        assert "collecting" in steps
        assert "parsing" in steps
        assert "ranking" in steps
        assert "writing" in steps
        assert done["result"]["status"] == "complete"


def test_query_jobs_done_incomplete(monkeypatch):
    async def fake_run(_job_id: str, user_input: str) -> Result:
        return _make_incomplete_result(user_input)

    monkeypatch.setattr(api_main, "_run_query_job", fake_run)

    with TestClient(api_main.app) as client:
        res = client.post("/query/jobs", json={"user_input": "백엔드 신입"})
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        done = None
        count = 0
        while count < 100:
            poll = client.get(f"/query/jobs/{job_id}")
            assert poll.status_code == 200
            payload = poll.json()
            if payload["status"] == "done":
                done = payload
                break
            time.sleep(0.02)
            count += 1

        assert done is not None
        assert done["job_id"] == job_id
        assert done["jobId"] == job_id
        assert done["result"]["status"] == "incomplete"
