import asyncio
import os
import time
import uuid
from contextlib import suppress
from typing import Literal, TypedDict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.state import Ask, Ner, Norm, Result, StrictBaseModel

app = FastAPI()
query_semaphore = None
job_queue = None
job_store = {}
job_store_lock = None
worker_tasks = []
cleanup_task = None


QueryJobState = Literal["queued", "running", "done", "failed"]
QueryStep = Literal["queued", "analyzing", "collecting", "parsing", "ranking", "writing"]

STEP_LABELS: dict[QueryStep, str] = {
    "queued": "대기열 처리 중",
    "analyzing": "질문 분석 중",
    "collecting": "공고 수집 중",
    "parsing": "공고 분석 중",
    "ranking": "맞춤 공고 선별 중",
    "writing": "답변 작성 중",
}

NODE_STEP_MAP: dict[str, QueryStep] = {
    "map_url": "collecting",
    "crawl_html": "parsing",
    "parse_job_info": "ranking",
    "search_hybrid": "writing",
}


class QueryJobEnvelope(StrictBaseModel):
    job_id: str
    jobId: str
    status: QueryJobState
    step: QueryStep | None = None
    step_label: str | None = None
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
    step: QueryStep | None
    step_label: str | None


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    step: QueryStep | None = None,
    step_label: str | None = None,
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
        record["step"] = step
        record["step_label"] = step_label


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
            "step": record["step"],
            "step_label": record["step_label"],
        }


async def _run_query_job(job_id: str, user_input: str) -> Result:
    from src.graph import get_compiled_graph

    loop = asyncio.get_running_loop()
    step_queue: asyncio.Queue[tuple[QueryStep, str]] = asyncio.Queue()
    state = _build_query_state(user_input)

    def push_step(step: QueryStep) -> None:
        label = STEP_LABELS[step]
        loop.call_soon_threadsafe(step_queue.put_nowait, (step, label))

    def run_stream() -> Result:
        graph = get_compiled_graph()
        final = dict(state)
        push_step("analyzing")

        for chunk in graph.stream(state, stream_mode="updates"):
            if not isinstance(chunk, dict):
                continue

            for name, data in chunk.items():
                if not isinstance(data, dict):
                    continue

                final.update(data)

                if name == "normalize_entities" and data.get("status") == "incomplete":
                    return _build_result(final, user_input)

                step = NODE_STEP_MAP.get(name)
                if step is not None:
                    push_step(step)

                if name == "generate_user_response":
                    return _build_result(final, user_input)

        return _build_result(final, user_input)

    thread_task = asyncio.create_task(asyncio.to_thread(run_stream))

    while not thread_task.done():
        try:
            step, label = await asyncio.wait_for(step_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            continue
        await _set_job_status(job_id, status="running", step=step, step_label=label)

    while not step_queue.empty():
        step, label = step_queue.get_nowait()
        await _set_job_status(job_id, status="running", step=step, step_label=label)

    return await thread_task


def _build_job_envelope(record: JobRecord) -> QueryJobEnvelope:
    message = record["message"]
    if record["status"] == "failed" and (message is None or not message):
        message = "job failed"

    return QueryJobEnvelope(
        job_id=record["job_id"],
        jobId=record["job_id"],
        status=record["status"],
        step=record["step"],
        step_label=record["step_label"],
        result=record["result"],
        message=message,
    )


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

            result = await _run_query_job(job_id, record["user_input"])
            await _set_job_status(job_id, status="done", result=result)
        except Exception as exc:
            await _set_job_status(job_id, status="failed", message=str(exc))
        finally:
            if job_queue is not None:
                job_queue.task_done()


async def cleanup_jobs_loop() -> None:
    ttl = int(os.getenv("JOB_RESULT_TTL_SECONDS", "600"))
    if ttl < 300:
        ttl = 300
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
async def startup():
    global query_semaphore
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


@app.on_event("shutdown")
async def shutdown():
    global cleanup_task, worker_tasks

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


@app.post("/query/jobs", response_model=QueryJobEnvelope, status_code=202)
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
        "step": "queued",
        "step_label": STEP_LABELS["queued"],
    }
    await _set_job_record(job_id, record)
    await job_queue.put(job_id)

    return QueryJobEnvelope(
        job_id=job_id,
        jobId=job_id,
        status="queued",
        step="queued",
        step_label=STEP_LABELS["queued"],
    )


@app.get(
    "/query/jobs/{job_id}",
    response_model=QueryJobEnvelope,
    responses={404: {"description": "Job not found"}},
)
async def get_query_job(job_id: str):
    record = await _get_job_record(job_id)
    if record is None:
        return JSONResponse(status_code=404, content={"message": "job not found"})

    if record["status"] == "done" and record["result"] is None:
        record["status"] = "failed"
        record["message"] = "job result missing"

    return _build_job_envelope(record)
