# 사람인에서 원하는 채용 공고를 찾아주는 AI

## 개발 환경 (uv 기준)

```bash
UV_CACHE_DIR=.uv-cache uv lock
UV_CACHE_DIR=.uv-cache uv sync
```

가상환경의 Python 실행:

```bash
UV_CACHE_DIR=.uv-cache uv run python -V
```

API 실행 예시:

```bash
UV_CACHE_DIR=.uv-cache uv run python -m src.api.job_search_api
```

선택 의존성 설치 예시:

```bash
# 검색/노트북/양자화 관련 의존성
UV_CACHE_DIR=.uv-cache uv sync --extra search --extra notebook --extra quant
```

`vllm`은 기본 설치가 아니라 optional extra(`llm-serving`)로 분리되어 있습니다.
