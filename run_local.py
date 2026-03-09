from src.graph import run_job_search_graph


def run(text):
    return run_job_search_graph({"user_input": text})


if __name__ == "__main__":
    # uv run langgraph dev
    # uv run python run_local.py
    result = run("서울 AI 엔지니어 신입 고졸 채용공고 찾아줘.")
    print(result)
