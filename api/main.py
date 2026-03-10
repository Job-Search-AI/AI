import asyncio
import os
import urllib.request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
ping_task = None
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


@app.post("/query")
def query(body: Body):
    from src.graph import run_job_search_graph

    result = run_job_search_graph({"user_input": body.user_input})
    if isinstance(result, dict):
        result.pop("retriever", None)
    return result
