import asyncio
import os
import urllib.request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()
ping_task = None
query_semaphore = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Body(BaseModel):
    user_input: str


async def ping_loop():
    url = os.getenv("SELF_PING_URL", "https://jobsearchai-e63j.onrender.com/health")
    sec = int(os.getenv("SELF_PING_INTERVAL_SECONDS", "300"))
    while True:
        await asyncio.sleep(sec)
        res = await asyncio.to_thread(urllib.request.urlopen, url, timeout=30)
        res.close()


@app.on_event("startup")
async def start_ping():
    global ping_task, query_semaphore
    query_limit = int(os.getenv("QUERY_CONCURRENCY", "1"))
    query_semaphore = asyncio.Semaphore(query_limit)

    if os.getenv("SELF_PING_ENABLED", "true") == "true":
        ping_task = asyncio.create_task(ping_loop())


@app.on_event("shutdown")
async def stop_ping():
    global ping_task
    if ping_task is not None:
        ping_task.cancel()
        ping_task = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
async def query(body: Body):
    from src.graph import run_job_search_graph

    global query_semaphore

    if query_semaphore is None:
        query_limit = int(os.getenv("QUERY_CONCURRENCY", "1"))
        query_semaphore = asyncio.Semaphore(query_limit)

    timeout = float(os.getenv("QUERY_BUSY_TIMEOUT_SECONDS", "2"))
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
        result = await asyncio.to_thread(
            run_job_search_graph,
            {"user_input": body.user_input},
        )
        if isinstance(result, dict):
            result.pop("retriever", None)
        return result
    finally:
        if acquired:
            query_semaphore.release()
