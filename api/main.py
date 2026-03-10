from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.state import Ask, Ner, Norm, Result

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
