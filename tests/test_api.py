import asyncio
import json
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


def _read_sse_events(response) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    event_name = None
    event_data = None

    for raw_line in response.iter_lines():
        line = raw_line
        if isinstance(raw_line, bytes):
            line = raw_line.decode("utf-8")

        if line == "":
            if event_name is not None:
                parsed_data = None
                if isinstance(event_data, str) and event_data:
                    parsed_data = json.loads(event_data)
                items.append({"event": event_name, "data": parsed_data})
            event_name = None
            event_data = None
            continue

        if line.startswith("event:"):
            event_name = line[6:].strip()
            continue

        if line.startswith("data:"):
            text = line[5:].strip()
            if event_data is None:
                event_data = text
            else:
                event_data = event_data + "\n" + text

    if event_name is not None:
        parsed_data = None
        if isinstance(event_data, str) and event_data:
            parsed_data = json.loads(event_data)
        items.append({"event": event_name, "data": parsed_data})

    return items


def _make_graph(chunks: list[dict[str, dict[str, object]]], error: str | None = None):
    def stream(_state, stream_mode="updates"):
        if stream_mode != "updates":
            raise AssertionError("stream_mode must be updates")

        idx = 0
        while idx < len(chunks):
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
    async def fake_run(body: Ask) -> Result:
        await asyncio.sleep(0.02)
        return _make_complete_result(body.user_input)

    monkeypatch.setattr(api_main, "_run_query_request", fake_run)

    with TestClient(api_main.app) as client:
        res = client.post("/query/jobs", json={"user_input": "서울 백엔드"})
        assert res.status_code == 202
        accepted = res.json()
        assert accepted["status"] == "queued"
        assert isinstance(accepted["jobId"], str)
        assert accepted["jobId"]

        job_id = accepted["jobId"]

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
        assert done["result"]["status"] == "complete"
        assert done["result"]["user_input"] == "서울 백엔드"


def test_query_jobs_failed(monkeypatch):
    async def fake_run(_body: Ask) -> Result:
        raise RuntimeError("boom")

    monkeypatch.setattr(api_main, "_run_query_request", fake_run)

    with TestClient(api_main.app) as client:
        res = client.post("/query/jobs", json={"user_input": "실패 케이스"})
        assert res.status_code == 202
        job_id = res.json()["jobId"]

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
        assert "boom" in failed["message"]


def test_query_jobs_not_found():
    with TestClient(api_main.app) as client:
        res = client.get("/query/jobs/not-found")
        assert res.status_code == 404
        assert res.json() == {"message": "job not found"}


def test_query_jobs_ttl_cleanup(monkeypatch):
    monkeypatch.setenv("JOB_RESULT_TTL_SECONDS", "1")
    monkeypatch.setenv("JOB_CLEANUP_INTERVAL_SECONDS", "1")

    async def fake_run(body: Ask) -> Result:
        return _make_complete_result(body.user_input)

    monkeypatch.setattr(api_main, "_run_query_request", fake_run)

    with TestClient(api_main.app) as client:
        res = client.post("/query/jobs", json={"user_input": "TTL 테스트"})
        assert res.status_code == 202
        job_id = res.json()["jobId"]

        count = 0
        while count < 100:
            poll = client.get(f"/query/jobs/{job_id}")
            assert poll.status_code == 200
            if poll.json()["status"] == "done":
                break
            time.sleep(0.02)
            count += 1

        time.sleep(2.2)

        expired = client.get(f"/query/jobs/{job_id}")
        assert expired.status_code == 404
        assert expired.json() == {"message": "job not found"}


def test_query_stream_complete_events_and_final_matches_query(monkeypatch):
    from src import graph as graph_module

    text = "서울 백엔드 신입 대졸 채용공고 찾아줘"
    entities = {"지역": "서울", "직무": "백엔드", "경력": "신입", "학력": "대졸"}
    normalized = {
        "지역": "서울",
        "직무": "백엔드/서버개발",
        "경력": "신입",
        "학력": "4년제대학교",
    }
    final_state = {
        "user_input": text,
        "query": text,
        "status": "complete",
        "message": "모든 정보가 확인되었습니다.",
        "entities": entities,
        "지역": "서울",
        "직무": "백엔드",
        "경력": "신입",
        "학력": "대졸",
        "missing_fields": None,
        "normalized_entities": normalized,
        "url": "https://example.com/jobs",
        "crawled_count": 2,
        "job_info_list": ["공고A", "공고B"],
        "retrieved_job_info_list": ["공고B"],
        "retrieved_scores": [0.91],
        "user_response": "추천 결과",
        "retriever": {"is_indexed": True},
    }
    chunks = [
        {
            "predict_entities": {
                "entities": entities,
                "지역": "서울",
                "직무": "백엔드",
                "경력": "신입",
                "학력": "대졸",
            }
        },
        {
            "normalize_entities": {
                "status": "complete",
                "message": "모든 정보가 확인되었습니다.",
                "missing_fields": None,
                "normalized_entities": normalized,
            }
        },
        {"map_url": {"url": "https://example.com/jobs"}},
        {"crawl_html": {"crawled_count": 2, "html_contents": ["<html>1</html>", "<html>2</html>"]}},
        {"parse_job_info": {"job_info_list": ["공고A", "공고B"]}},
        {"search_hybrid": {"retriever": {"is_indexed": True}, "retrieved_job_info_list": ["공고B"], "retrieved_scores": [0.91]}},
        {"generate_user_response": {"user_response": "추천 결과"}},
    ]

    monkeypatch.setattr(graph_module, "run_job_search_graph", lambda _state: dict(final_state))
    monkeypatch.setattr(graph_module, "get_compiled_graph", lambda: _make_graph(chunks))

    with TestClient(api_main.app) as client:
        sync_res = client.post("/query", json={"user_input": text})
        assert sync_res.status_code == 200
        sync_data = sync_res.json()

        with client.stream("POST", "/query/stream", json={"user_input": text}) as stream_res:
            assert stream_res.status_code == 200
            events = _read_sse_events(stream_res)

    step_values = []
    final_data = None
    error_data = None
    for item in events:
        if item["event"] == "step":
            payload = item["data"]
            if isinstance(payload, dict):
                step_values.append(payload.get("step"))
        if item["event"] == "final":
            final_data = item["data"]
        if item["event"] == "error":
            error_data = item["data"]

    assert step_values == ["analyzing", "collecting", "parsing", "ranking", "writing"]
    assert error_data is None
    assert isinstance(final_data, dict)
    assert final_data == sync_data


def test_query_stream_incomplete_events_and_final_matches_query(monkeypatch):
    from src import graph as graph_module

    text = "백엔드 신입 채용공고 찾아줘"
    entities = {"지역": "", "직무": "백엔드", "경력": "신입", "학력": ""}
    normalized = {"지역": None, "직무": "백엔드/서버개발", "경력": "신입", "학력": None}
    final_state = {
        "user_input": text,
        "query": text,
        "status": "incomplete",
        "message": "지역, 학력 정보를 알려주세요.",
        "entities": entities,
        "지역": "",
        "직무": "백엔드",
        "경력": "신입",
        "학력": "",
        "missing_fields": ["지역", "학력"],
        "normalized_entities": normalized,
    }
    chunks = [
        {
            "predict_entities": {
                "entities": entities,
                "지역": "",
                "직무": "백엔드",
                "경력": "신입",
                "학력": "",
            }
        },
        {
            "normalize_entities": {
                "status": "incomplete",
                "message": "지역, 학력 정보를 알려주세요.",
                "missing_fields": ["지역", "학력"],
                "normalized_entities": normalized,
            }
        },
    ]

    monkeypatch.setattr(graph_module, "run_job_search_graph", lambda _state: dict(final_state))
    monkeypatch.setattr(graph_module, "get_compiled_graph", lambda: _make_graph(chunks))

    with TestClient(api_main.app) as client:
        sync_res = client.post("/query", json={"user_input": text})
        assert sync_res.status_code == 200
        sync_data = sync_res.json()

        with client.stream("POST", "/query/stream", json={"user_input": text}) as stream_res:
            assert stream_res.status_code == 200
            events = _read_sse_events(stream_res)

    step_values = []
    step_labels = []
    final_data = None
    error_data = None
    for item in events:
        if item["event"] == "step":
            payload = item["data"]
            if isinstance(payload, dict):
                step_values.append(payload.get("step"))
                step_labels.append(payload.get("label"))
        if item["event"] == "final":
            final_data = item["data"]
        if item["event"] == "error":
            error_data = item["data"]

    assert step_values == ["analyzing", "need_more_info"]
    assert step_labels == ["질문 분석 중", "추가 정보 확인 중"]
    assert error_data is None
    assert isinstance(final_data, dict)
    assert final_data["status"] == "incomplete"
    assert final_data == sync_data


def test_query_stream_error_event_without_final(monkeypatch):
    from src import graph as graph_module

    monkeypatch.setattr(graph_module, "get_compiled_graph", lambda: _make_graph([], error="boom"))

    with TestClient(api_main.app) as client:
        with client.stream("POST", "/query/stream", json={"user_input": "에러 테스트"}) as stream_res:
            assert stream_res.status_code == 200
            events = _read_sse_events(stream_res)

    event_names = []
    error_data = None
    final_data = None
    for item in events:
        event_names.append(item["event"])
        if item["event"] == "error":
            error_data = item["data"]
        if item["event"] == "final":
            final_data = item["data"]

    assert event_names == ["step", "error"]
    assert final_data is None
    assert isinstance(error_data, dict)
    assert "boom" in error_data["message"]
