import asyncio
import os
import urllib.request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.state import Ask, Ner, Norm, Result

app = FastAPI()
ping_task = None
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


@app.on_event("startup")
async def start_ping():
    global ping_task
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


@app.post("/query", response_model=Result)
def query(body: Ask):
    from src.graph import run_job_search_graph

    result = run_job_search_graph({"user_input": body.user_input})
    entities = None
    normalized_entities = None

    if isinstance(result.get("entities"), dict):
        entities = Ner.model_validate(result["entities"])
    if isinstance(result.get("normalized_entities"), dict):
        normalized_entities = Norm.model_validate(result["normalized_entities"])

    return Result(
        user_input=result["user_input"],
        query=result["query"],
        status=result["status"],
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
