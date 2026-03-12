import asyncio
import json
import os
import urllib.request

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

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
        query=result.get("query", body.user_input),
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


@app.post("/query/stream")
def query_stream(body: Ask):
    from src.graph import get_compiled_graph

    def event_stream():
        def event_line(name: str, data: dict):
            text = json.dumps(jsonable_encoder(data), ensure_ascii=False)
            return f"event: {name}\ndata: {text}\n\n"

        state = {"user_input": body.user_input, "retrieval_top_k": 5}
        if body.user_input.strip():
            state["query"] = body.user_input

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
                        entities = None
                        normalized_entities = None
                        if isinstance(final.get("entities"), dict):
                            entities = Ner.model_validate(final["entities"])
                        if isinstance(final.get("normalized_entities"), dict):
                            normalized_entities = Norm.model_validate(final["normalized_entities"])

                        yield event_line(
                            "step",
                            {"step": "need_more_info", "label": "추가 정보 확인 필요"},
                        )
                        yield event_line(
                            "final",
                            Result(
                                user_input=final["user_input"],
                                query=final.get("query", body.user_input),
                                status=final["status"],
                                message=final.get("message"),
                                entities=entities,
                                loc=final.get("지역"),
                                job=final.get("직무"),
                                exp=final.get("경력"),
                                edu=final.get("학력"),
                                missing_fields=final.get("missing_fields"),
                                normalized_entities=normalized_entities,
                                url=final.get("url"),
                                crawled_count=final.get("crawled_count"),
                                job_info_list=final.get("job_info_list"),
                                retrieved_job_info_list=final.get("retrieved_job_info_list"),
                                retrieved_scores=final.get("retrieved_scores"),
                                user_response=final.get("user_response"),
                            ).model_dump(by_alias=True),
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
                        entities = None
                        normalized_entities = None
                        if isinstance(final.get("entities"), dict):
                            entities = Ner.model_validate(final["entities"])
                        if isinstance(final.get("normalized_entities"), dict):
                            normalized_entities = Norm.model_validate(final["normalized_entities"])

                        yield event_line(
                            "final",
                            Result(
                                user_input=final["user_input"],
                                query=final.get("query", body.user_input),
                                status=final["status"],
                                message=final.get("message"),
                                entities=entities,
                                loc=final.get("지역"),
                                job=final.get("직무"),
                                exp=final.get("경력"),
                                edu=final.get("학력"),
                                missing_fields=final.get("missing_fields"),
                                normalized_entities=normalized_entities,
                                url=final.get("url"),
                                crawled_count=final.get("crawled_count"),
                                job_info_list=final.get("job_info_list"),
                                retrieved_job_info_list=final.get("retrieved_job_info_list"),
                                retrieved_scores=final.get("retrieved_scores"),
                                user_response=final.get("user_response"),
                            ).model_dump(by_alias=True),
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
