# Legacy 디렉토리 안내

## 이동 이유
- LangGraph 실행 경로(`src/graph.py`, `src/node.py`, `src/router.py`, `src/state`, `src/tools`)를 기준으로 `src`를 최소 코어 구조로 정리했다.
- 코어 외부 모듈은 실행 의존을 `src/tools/**`로 흡수한 뒤 원본을 `legacy/`로 이동해, 원본 코드 보존과 실행 경로 단순화를 동시에 맞췄다.

## 경로 매핑
| 이전 경로 | 현재 경로 |
| --- | --- |
| `main.py` | `legacy/api/main.py` |
| `src/bert_crf/` | `legacy/src/bert_crf/` |
| `src/entity_normalizer/` | `legacy/src/entity_normalizer/` |
| `src/url_mapper/` | `legacy/src/url_mapper/` |
| `src/url_exchanger/` | `legacy/src/url_exchanger/` |
| `src/evaluation/` | `legacy/src/evaluation/` |
| `src/retrieval/test_hybrid_retrieval.py` | `legacy/src/retrieval/test_hybrid_retrieval.py` |
| `src/utils/model_keeper.py` | `legacy/src/utils/model_keeper.py` |
| `src/crawling/` | `legacy/src/crawling/` |
| `src/parsing/` | `legacy/src/parsing/` |
| `src/retrieval/` | `legacy/src/retrieval/` |
| `src/embedding/` | `legacy/src/embedding/` |
| `src/llm/` | `legacy/src/llm/` |
| `src/search/` | `legacy/src/search/` |
| `src/singletone_model/` | `legacy/src/singletone_model/` |
| `src/utils/` | `legacy/src/utils/` |
| `notebooks/url_exchanger/` | `legacy/notebooks/url_exchanger/` |

## src 최종 구조
- 유지: `src/graph.py`, `src/node.py`, `src/router.py`, `src/state/**`, `src/tools/**`, `src/__init__.py`
- 제거: `src/crawling`, `src/parsing`, `src/retrieval`, `src/embedding`, `src/llm`, `src/search`, `src/singletone_model`, `src/utils`

## 호환 범위 및 제한
- 유지되는 공개 API:
  - `src.predict_crf_bert`
  - `src.normalize_and_validate_entities`
  - `src.keep_loading_job_model`
  - `src.mapping_url_query`
- 직접 import 경로 호환은 유지하지 않는다. `src.crawling.*`, `src.parsing.*` 등 구경로는 런타임 보장 대상이 아니다.
- 레거시 코드 재사용이 필요하면 `legacy.src.*` 경로를 직접 사용한다.
