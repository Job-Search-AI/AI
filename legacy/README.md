# Legacy 디렉토리 안내

## 이동 이유
- LangGraph 실행 경로(`src/graph.py`, `src/node.py`, `src/state`, `src/tools`)를 중심으로 현재 운영 코드를 명확히 분리하기 위해 레거시 코드를 `legacy/`로 이동했다.
- 기존 `from src import ...` 공개 API는 유지하고, 내부 lazy import 경로만 `legacy`로 연결해 하위 호환을 유지한다.

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
| `notebooks/url_exchanger/` | `legacy/notebooks/url_exchanger/` |

## 호환 범위
- 유지되는 공개 API:
  - `src.predict_crf_bert`
  - `src.normalize_and_validate_entities`
  - `src.keep_loading_job_model`
  - `src.mapping_url_query`
- 직접 import 경로(`src.url_mapper.*`, `src.entity_normalizer.*`, `src.bert_crf.*`, `src.url_exchanger.*`, `src.evaluation.*`)는 이제 `legacy.src.*` 사용을 권장한다.
