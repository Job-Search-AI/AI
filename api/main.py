import asyncio
import json
import os
import time
import urllib.request
import uuid
from contextlib import suppress
from typing import Literal, TypedDict

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from src.state import Ask, Ner, Norm, Result, StrictBaseModel

app = FastAPI()
ping_task = None
query_semaphore = None
job_queue = None
job_store = {}
job_store_lock = None
worker_tasks = []
cleanup_task = None


QueryJobState = Literal["queued", "running", "done", "failed"]


class QueryJobAccepted(StrictBaseModel):
    jobId: str
    status: Literal["queued"]


class QueryJobStatus(StrictBaseModel):
    jobId: str
    status: QueryJobState
    result: Result | None = None
    message: str | None = None


class JobRecord(TypedDict):
    job_id: str
    user_input: str
    status: QueryJobState
    created_at: float
    updated_at: float
    result: Result | None
    message: str | None


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def ping_loop():
    url = os.getenv("SELF_PING_URL", "https://jobsearchai-e63j.onrender.com/health")
    sec = int(os.getenv("SELF_PING_INTERVAL_SECONDS", "300"))
    while True:
        await asyncio.sleep(sec)
        res = await asyncio.to_thread(urllib.request.urlopen, url, timeout=30)
        res.close()


def _build_query_state(user_input: str) -> dict[str, object]:
    state: dict[str, object] = {"user_input": user_input, "retrieval_top_k": 5}
    if user_input.strip():
        state["query"] = user_input
    return state


def _build_result(state: dict[str, object], user_input: str) -> Result:
    result = dict(state)
    result.pop("retriever", None)

    entities = None
    normalized_entities = None

    if isinstance(result.get("entities"), dict):
        entities = Ner.model_validate(result["entities"])
    if isinstance(result.get("normalized_entities"), dict):
        normalized_entities = Norm.model_validate(result["normalized_entities"])

    status = result.get("status")
    if status not in ("complete", "incomplete"):
        raise ValueError("query result status is invalid")

    query = result.get("query", user_input)
    if not isinstance(query, str):
        query = user_input

    return Result(
        user_input=result.get("user_input", user_input),
        query=query,
        status=status,
        message=result.get("message"),
        entities=entities,
        loc=result.get("지역"),
        job=result.get("직무"),
        exp=result.get("경력"),
        edu=result.get("학력"),
        missing_fields=result.get("missing_fields"),
        normalized_entities=normalized_entities,
        url=result.get("url"),
        crawled_count=result.get("crawled_count"),
        job_info_list=result.get("job_info_list"),
        retrieved_job_info_list=result.get("retrieved_job_info_list"),
        retrieved_scores=result.get("retrieved_scores"),
        user_response=result.get("user_response"),
    )


async def _run_query_request(body: Ask) -> Result:
    from src.graph import run_job_search_graph

    state = _build_query_state(body.user_input)
    result = await asyncio.to_thread(
        run_job_search_graph,
        state,
    )
    if not isinstance(result, dict):
        raise ValueError("query result must be a dict")
    return _build_result(result, body.user_input)


async def _get_job_store_lock() -> asyncio.Lock:
    global job_store_lock
    if job_store_lock is None:
        job_store_lock = asyncio.Lock()
    return job_store_lock


async def _set_job_record(job_id: str, record: JobRecord) -> None:
    lock = await _get_job_store_lock()
    async with lock:
        job_store[job_id] = record


async def _set_job_status(
    job_id: str,
    status: QueryJobState,
    result: Result | None = None,
    message: str | None = None,
) -> None:
    lock = await _get_job_store_lock()
    async with lock:
        record = job_store.get(job_id)
        if record is None:
            return
        record["status"] = status
        record["updated_at"] = time.time()
        record["result"] = result
        record["message"] = message


async def _get_job_record(job_id: str) -> JobRecord | None:
    lock = await _get_job_store_lock()
    async with lock:
        record = job_store.get(job_id)
        if record is None:
            return None
        return {
            "job_id": record["job_id"],
            "user_input": record["user_input"],
            "status": record["status"],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
            "result": record["result"],
            "message": record["message"],
        }


async def query_worker() -> None:
    global job_queue

    while True:
        if job_queue is None:
            await asyncio.sleep(0.1)
            continue

        job_id = await job_queue.get()
        try:
            record = await _get_job_record(job_id)
            if record is None:
                continue

            await _set_job_status(job_id, status="running")
            body = Ask(user_input=record["user_input"])
            result = await _run_query_request(body)
            await _set_job_status(job_id, status="done", result=result)
        except Exception as exc:
            await _set_job_status(job_id, status="failed", message=str(exc))
        finally:
            if job_queue is not None:
                job_queue.task_done()


async def cleanup_jobs_loop() -> None:
    ttl = int(os.getenv("JOB_RESULT_TTL_SECONDS", "600"))
    interval = int(os.getenv("JOB_CLEANUP_INTERVAL_SECONDS", "30"))

    while True:
        await asyncio.sleep(interval)
        now = time.time()
        expired_ids = []

        lock = await _get_job_store_lock()
        async with lock:
            for job_id, record in job_store.items():
                if record["status"] != "done" and record["status"] != "failed":
                    continue
                if now - record["updated_at"] < ttl:
                    continue
                expired_ids.append(job_id)

            for job_id in expired_ids:
                job_store.pop(job_id, None)


@app.on_event("startup")
async def start_ping():
    global ping_task, query_semaphore
    global job_queue, job_store_lock, worker_tasks, cleanup_task

    query_limit = int(os.getenv("QUERY_CONCURRENCY", "1"))
    if query_limit < 1:
        query_limit = 1

    query_semaphore = asyncio.Semaphore(query_limit)
    job_queue = asyncio.Queue()
    job_store.clear()
    job_store_lock = asyncio.Lock()

    worker_tasks = []
    index = 0
    while index < query_limit:
        worker_tasks.append(asyncio.create_task(query_worker()))
        index += 1

    cleanup_task = asyncio.create_task(cleanup_jobs_loop())

    if os.getenv("SELF_PING_ENABLED", "true") == "true":
        ping_task = asyncio.create_task(ping_loop())


@app.on_event("shutdown")
async def stop_ping():
    global ping_task
    global cleanup_task, worker_tasks

    if ping_task is not None:
        ping_task.cancel()
        with suppress(asyncio.CancelledError):
            await ping_task
        ping_task = None

    for task in worker_tasks:
        task.cancel()
    for task in worker_tasks:
        with suppress(asyncio.CancelledError):
            await task
    worker_tasks = []

    if cleanup_task is not None:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        cleanup_task = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=Result, responses={429: {"description": "Busy"}})
async def query(body: Ask):
    global query_semaphore

    if query_semaphore is None:
        query_limit = int(os.getenv("QUERY_CONCURRENCY", "1"))
        if query_limit < 1:
            query_limit = 1
        query_semaphore = asyncio.Semaphore(query_limit)

    timeout = float(os.getenv("QUERY_BUSY_TIMEOUT_SECONDS", "45"))
    acquired = False

    try:
        await asyncio.wait_for(query_semaphore.acquire(), timeout=timeout)
        acquired = True
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=429,
            content={
                "status": "busy",
                "message": "요청이 많습니다. 잠시 후 다시 시도해주세요.",
            },
        )

    try:
        return await _run_query_request(body)
    finally:
        if acquired:
            query_semaphore.release()


@app.post("/query/jobs", response_model=QueryJobAccepted, status_code=202)
async def create_query_job(body: Ask):
    global job_queue

    if job_queue is None:
        job_queue = asyncio.Queue()

    job_id = uuid.uuid4().hex
    now = time.time()
    record: JobRecord = {
        "job_id": job_id,
        "user_input": body.user_input,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "result": None,
        "message": None,
    }
    await _set_job_record(job_id, record)
    await job_queue.put(job_id)

    return QueryJobAccepted(jobId=job_id, status="queued")


@app.get(
    "/query/jobs/{job_id}",
    response_model=QueryJobStatus,
    responses={404: {"description": "Job not found"}},
)
async def get_query_job(job_id: str):
    record = await _get_job_record(job_id)
    if record is None:
        return JSONResponse(status_code=404, content={"message": "job not found"})

    status = record["status"]
    if status == "queued" or status == "running":
        return QueryJobStatus(jobId=job_id, status=status)

    if status == "done":
        if record["result"] is None:
            return QueryJobStatus(jobId=job_id, status="failed", message="job result missing")
        return QueryJobStatus(jobId=job_id, status="done", result=record["result"])

    message = record["message"]
    if message is None or not message:
        message = "job failed"
    return QueryJobStatus(jobId=job_id, status="failed", message=message)


@app.post("/query/stream")
def query_stream(body: Ask):
    from src.graph import get_compiled_graph

    def event_stream():
        def event_line(name: str, data: dict):
            text = json.dumps(jsonable_encoder(data), ensure_ascii=False)
            return f"event: {name}\ndata: {text}\n\n"

        state = _build_query_state(body.user_input)
        final = dict(state)

        try:
            yield event_line("step", {"step": "analyzing", "label": "질문 분석 중"})
            graph = get_compiled_graph()
            done = False

            for chunk in graph.stream(state, stream_mode="updates"):
                if not isinstance(chunk, dict):
                    continue

                for name, data in chunk.items():
                    if not isinstance(data, dict):
                        continue

                    final.update(data)

                    if name == "normalize_entities" and data.get("status") == "incomplete":
                        yield event_line(
                            "step",
                            {"step": "need_more_info", "label": "추가 정보 확인 중"},
                        )
                        yield event_line(
                            "final",
                            _build_result(final, body.user_input).model_dump(by_alias=True),
                        )
                        done = True
                        break

                    if name == "map_url":
                        yield event_line("step", {"step": "collecting", "label": "공고 수집 중"})
                    if name == "crawl_html":
                        yield event_line("step", {"step": "parsing", "label": "공고 분석 중"})
                    if name == "parse_job_info":
                        yield event_line("step", {"step": "ranking", "label": "맞춤 공고 선별 중"})
                    if name == "search_hybrid":
                        yield event_line("step", {"step": "writing", "label": "답변 작성 중"})
                    if name == "generate_user_response":
                        yield event_line(
                            "final",
                            _build_result(final, body.user_input).model_dump(by_alias=True),
                        )
                        done = True
                        break

                if done:
                    break
        except Exception as exc:
            yield event_line("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
