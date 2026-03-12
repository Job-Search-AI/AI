import asyncio
import json
import os
import urllib.request

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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


@app.post("/query/stream")
def query_stream(body: Body):
    from src.graph import get_compiled_graph

    def event_stream():
        def event_line(event_name: str, event_data: dict):
            payload = json.dumps(jsonable_encoder(event_data), ensure_ascii=False)
            return f"event: {event_name}\ndata: {payload}\n\n"

        state = {"user_input": body.user_input, "retrieval_top_k": 5}
        if body.user_input.strip():
            state["query"] = body.user_input

        final_state = dict(state)

        try:
            yield event_line("step", {"step": "analyzing", "label": "질문 분석 중"})
            graph = get_compiled_graph()
            done = False

            for chunk in graph.stream(state, stream_mode="updates"):
                if not isinstance(chunk, dict):
                    continue

                for node_name, update in chunk.items():
                    if not isinstance(update, dict):
                        continue

                    final_state.update(update)

                    if node_name == "normalize_entities" and update.get("status") == "incomplete":
                        yield event_line(
                            "step",
                            {"step": "need_more_info", "label": "추가 정보 확인 필요"},
                        )
                        out = dict(final_state)
                        out.pop("retriever", None)
                        yield event_line("final", out)
                        done = True
                        break

                    if node_name == "map_url":
                        yield event_line("step", {"step": "collecting", "label": "공고 수집 중"})
                    if node_name == "crawl_html":
                        yield event_line("step", {"step": "parsing", "label": "공고 분석 중"})
                    if node_name == "parse_job_info":
                        yield event_line("step", {"step": "ranking", "label": "맞춤 공고 선별 중"})
                    if node_name == "search_hybrid":
                        yield event_line("step", {"step": "writing", "label": "답변 작성 중"})
                    if node_name == "generate_user_response":
                        out = dict(final_state)
                        out.pop("retriever", None)
                        yield event_line("final", out)
                        done = True
                        break

                if done:
                    break

            if not done:
                out = dict(final_state)
                out.pop("retriever", None)
                yield event_line("final", out)
        except Exception as exc:
            yield event_line("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
