from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Body(BaseModel):
    user_input: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(body: Body):
    from src.graph import run_job_search_graph

    return run_job_search_graph({"user_input": body.user_input})
