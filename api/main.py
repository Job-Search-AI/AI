from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Body(BaseModel):
    user_input: str


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
