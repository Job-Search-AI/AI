# AI 기반 채용공고 검색 시스템

> `develop` 브랜치 기준 README  
> 자연어 기반 채용공고 검색을 위해 슬롯 추출, 정규화, 크롤링, 하이브리드 검색, 응답 생성을 결합한 AI 채용 검색 시스템

[프론트엔드 데모 바로가기](https://job-search-ai.netlify.app/)

| 항목 | 내용 |
| --- | --- |
| 해결 문제 | 자연어 채용 검색 요청을 구조화된 검색 조건으로 변환하고, 실제 공고를 수집·선별·요약해 추천 |
| 핵심 강점 | LangGraph 파이프라인, BM25+임베딩 하이브리드 검색, 비동기 Job Polling API, Docker/GCP 배포 |
| 정량 성과 | NER Micro F1 `0.9214`, Hybrid `nDCG@5 0.7015`, Crawl CSR `0.9565`, E2E 평균 `4.83s` |
| 데모 | 프론트엔드: [https://job-search-ai.netlify.app/](https://job-search-ai.netlify.app/) |

## 1. 한 줄 소개

자연어 기반 채용공고 검색을 위해 슬롯 추출, 정규화, 크롤링, 하이브리드 검색, 응답 생성을 결합한 AI 채용 검색 시스템입니다.

## 2. 해결하려는 문제

일반적인 채용 검색은 `백엔드`, `서울`, `신입`처럼 키워드를 직접 조합해야 하고, 여러 조건이 섞인 자연어 요청을 안정적으로 반영하기 어렵습니다. 실제 사용자는 `서울 백엔드 신입 대졸 채용공고 찾아줘`처럼 지역, 직무, 경력, 학력 조건을 한 문장으로 입력하기 때문에, 단순 키워드 검색만으로는 원하는 공고를 빠르게 찾기 어렵습니다.

이 프로젝트는 자연어 질의를 그대로 받되, 내부적으로는 `지역 / 직무 / 경력 / 학력` 슬롯으로 구조화하고, 이를 실제 검색 URL과 공고 수집 파이프라인에 연결해 조건에 맞는 공고를 추천합니다. 구현 자체보다도, `얼마나 동작하는지`, `왜 이 구조를 선택했는지`, `운영 시 어떤 문제가 있었고 어떻게 개선했는지`까지 보이도록 설계와 평가를 함께 정리했습니다.

## 3. 핵심 기능

- 자연어 질의에서 `지역 / 직무 / 경력 / 학력` 슬롯 추출
- 동의어 사전 기반 슬롯 정규화와 누락 정보 안내
- 정규화된 슬롯을 사람인 검색 URL로 변환
- `view-ajax` 기반 상세 공고 수집과 교육성 공고 필터링
- 공고 제목, 요약, 상세, 지원 방법, 기업 정보, 복리후생, 지원자 통계 파싱
- BM25 + 임베딩 기반 하이브리드 검색으로 상위 공고 선별
- 상위 결과를 바탕으로 최종 추천 응답 생성
- 동기 `POST /query` API와 비동기 Job Polling API 제공
- 진행 상태를 `queued -> running -> done / failed`와 단계 라벨로 노출

### 사용자 흐름

`사용자 입력 -> 슬롯 추출 -> 슬롯 정규화 -> 정보 부족 시 incomplete 종료 -> URL 매핑 -> 공고 수집 -> 공고 파싱 -> 하이브리드 검색 -> 최종 응답 생성`

## 4. 시스템 아키텍처

### LangGraph 파이프라인

현재 실제 LangGraph 흐름은 아래와 같습니다.

`singleton_model -> predict_entities -> normalize_entities -> incomplete_end | map_url -> crawl_html -> parse_job_info -> search_hybrid -> generate_user_response`

<img src="img/Option%20A_B%20Decision%20Flow-2026-03-04-093254.png" width="300">

### 단계별 구조

| 단계 | 역할 | 핵심 출력 |
| --- | --- | --- |
| `singleton_model` | 모델 캐시 초기화 및 재사용 | NER/임베딩/응답 생성 리소스 |
| `predict_entities` | 사용자 입력에서 슬롯 추출 | `지역`, `직무`, `경력`, `학력` |
| `normalize_entities` | 동의어 정규화 및 필수 슬롯 검증 | `normalized_entities`, `missing_fields`, `status` |
| `map_url` | 검색 가능한 사람인 URL 생성 | `url` |
| `crawl_html` | `view-ajax` 기반 상세 공고 수집 | `html_contents`, `crawled_count` |
| `parse_job_info` | HTML을 읽기 쉬운 공고 텍스트로 변환 | `job_info_list` |
| `search_hybrid` | BM25 + 임베딩 기반 상위 공고 선별 | `retrieved_job_info_list`, `retrieved_scores` |
| `generate_user_response` | 상위 공고를 바탕으로 최종 추천 문장 생성 | `user_response` |

### 설계 의사결정

| 설계 선택 | 이유 |
| --- | --- |
| LangGraph 사용 | 검색 플로우가 단순 함수 호출이 아니라 `정상 검색`과 `정보 부족 종료` 분기를 갖기 때문에, 파이프라인과 상태 전이를 명시적으로 관리하기 위해 선택했습니다. |
| `node / state / tools` 분리 | 오케스트레이션, 상태 계약, 도메인 로직을 분리해 유지보수성과 확장성을 높였습니다. |
| OpenAI 경로 + 로컬 fallback 유지 | 운영 환경과 실험 환경을 모두 고려해 OpenAI structured output 경로와 로컬 모델 경로를 함께 유지했습니다. |
| 비동기 Job Polling 구조 도입 | 장시간 동기 요청으로 인한 타임아웃과 사용자 대기 문제를 줄이기 위해 `/query/jobs` 기반 비동기 흐름을 추가했습니다. |
| `view-ajax` 기반 수집 | raw HTML만으로는 상세 공고 핵심 정보가 누락되는 문제가 있어, 브라우저 전체 렌더링보다 가벼우면서도 정확도를 유지할 수 있는 `view-ajax` 수집 방식으로 전환했습니다. |
| 추천 공고 1건 고정 | 최종 응답이 여러 공고를 애매하게 섞는 문제를 줄이기 위해, 리트리버 1위 공고를 기준으로 추천 대상을 고정했습니다. |

### REST API 요약

#### `GET /health`

| 항목 | 내용 |
| --- | --- |
| 목적 | 서버 상태 확인 |
| 요청 필드 | 없음 |
| 주요 응답 필드 | `status` |
| 상태값 의미 | `ok`: 서버가 요청을 받을 수 있는 상태 |

#### `POST /query`

| 항목 | 내용 |
| --- | --- |
| 목적 | 동기 방식으로 채용 검색 요청을 즉시 처리 |
| 요청 필드 | `user_input: string` |
| 주요 응답 필드 | `status`, `message`, `entities`, `missing_fields`, `normalized_entities`, `url`, `crawled_count`, `retrieved_job_info_list`, `retrieved_scores`, `user_response` |
| 상태값 의미 | `complete`: 검색과 응답 생성까지 완료, `incomplete`: 필수 슬롯이 부족해 추가 입력 필요 |

#### `POST /query/jobs`

| 항목 | 내용 |
| --- | --- |
| 목적 | 장시간 검색 작업을 비동기로 접수 |
| 요청 필드 | `user_input: string` |
| 주요 응답 필드 | `job_id`, `jobId`, `status`, `step`, `step_label` |
| 상태값 의미 | `queued`: 대기열 등록 완료 |

#### `GET /query/jobs/{job_id}`

| 항목 | 내용 |
| --- | --- |
| 목적 | 비동기 검색 작업의 현재 상태 조회 |
| 요청 필드 | 경로 파라미터 `job_id` |
| 주요 응답 필드 | `status`, `step`, `step_label`, `result`, `message` |
| 상태값 의미 | `queued`: 대기 중, `running`: 처리 중, `done`: 완료, `failed`: 실패 |

#### Job 상태값

| 상태값 | 의미 |
| --- | --- |
| `queued` | 작업이 큐에 접수된 상태 |
| `running` | 워커가 검색 작업을 수행 중인 상태 |
| `done` | 결과 생성이 완료된 상태 |
| `failed` | 처리 중 예외가 발생한 상태 |

#### Job 단계값

| 단계값 | 의미 |
| --- | --- |
| `queued` | 대기열 처리 중 |
| `analyzing` | 질문 분석 중 |
| `collecting` | 공고 수집 중 |
| `parsing` | 공고 분석 중 |
| `ranking` | 맞춤 공고 선별 중 |
| `writing` | 답변 작성 중 |

### 아키텍처 관점에서 강조하고 싶은 점

- 정보가 부족하면 무리하게 검색을 진행하지 않고 `incomplete`로 종료해 추가 정보를 요청합니다.
- 검색, 파싱, 응답 생성 전 단계가 상태 기반으로 분리되어 있어 병목 지점과 실패 지점을 추적하기 쉽습니다.
- 운영 환경에서는 동시성 제한, 메모리 로그, TTL 정리, Job 상태 조회 같은 안정성 장치가 포함되어 있습니다.

## 5. 기술 스택

| 구분 | 기술 | 사용 목적 |
| --- | --- | --- |
| Language | Python 3.12 | API, 크롤링, 검색, 평가 스크립트 전반 구현 |
| Package Manager | uv | 개발 환경 재현성과 의존성 관리 단순화 |
| API | FastAPI | 동기/비동기 채용 검색 API 제공 |
| Orchestration | LangGraph | 단계별 상태 전이와 분기 흐름 관리 |
| NER | OpenAI structured output, 로컬 BERT+CRF fallback | 슬롯 추출 일관성 확보와 fallback 경로 유지 |
| Retrieval | BM25, OpenAI Embeddings, 로컬 임베딩 fallback | 키워드 일치와 의미 유사도를 함께 반영한 검색 |
| Crawling | requests, BeautifulSoup, lxml | `view-ajax` 기반 상세 공고 수집 및 HTML 파싱 |
| Parsing | BeautifulSoup 기반 커스텀 파서 | 공고 텍스트를 검색 가능한 문서 형태로 정리 |
| Infra | Docker | 실행 환경을 컨테이너로 표준화 |
| Deployment | Netlify, GCP VM, Cloud Build | 프론트 공개 배포와 백엔드 자동 롤아웃 구성 |
| Ops | systemd, Nginx | VM에서 서비스 재시작과 리버스 프록시 처리 |

## 6. 성능/평가 지표

프로젝트를 단순 기능 구현으로 끝내지 않고, `슬롯 추출`, `크롤링`, `검색`, `최종 응답`, `E2E 운영 성능`까지 각각 측정 가능한 형태로 정리했습니다.

### 6.1 NER 평가

OpenAI `json_schema` 기반 슬롯 추출 경로를 50건 기준으로 평가했습니다. 아래 수치는 전체 문장 정확도가 아니라 슬롯 추출 기준의 성능이며, `0.9214`는 slot-level micro F1입니다.

| 지표 | 값 |
| --- | ---: |
| Micro F1 | `0.9214` |
| Macro F1 | `0.9099` |
| 문장 단위 Exact Match | `53.06%` |
| 실패 호출 수 | `1 / 50` |

| 슬롯 | 정확도 | 해석 |
| --- | ---: | --- |
| 지역 | `54.00%` | 세부 지역 표현을 상위 canonical 값으로 정규화하는 단계가 주요 약점 |
| 직무 | `94.00%` | 직무 추출은 비교적 안정적 |
| 경력 | `95.92%` | 신입/경력 표현 추출 정확도가 높음 |
| 학력 | `98.00%` | 학력 추출은 가장 안정적 |

### 6.2 크롤링 KPI

2026-03-15 ~ 2026-03-16 기준 크롤링 운영 지표입니다.

| 지표 | 값 | 의미 |
| --- | ---: | --- |
| CSR | `0.9565` | 전체 시도 대비 성공 수집 비율 |
| VPCR | `0.9091` | 성공 수집 중 유효 공고 비율 |
| duplicate_rate | `0.0455` | 중복 공고 비율 |
| invalid_rate | `0.0455` | 유효하지 않은 공고 비율 |

| 원본 통계 | 값 |
| --- | ---: |
| attempt | `23` |
| success | `22` |
| valid | `20` |
| duplicate | `1` |
| invalid | `1` |

### 6.3 검색/랭킹 품질

오프라인 검색 평가 기준, Hybrid 방식이 BM25와 OpenAI Embedding 단독 방식보다 더 높은 성능을 기록했습니다.

| 방법 | nDCG@5 | Recall@5 | MRR@5 |
| --- | ---: | ---: | ---: |
| BM25 | `0.6482` | `0.6624` | `0.7421` |
| Hybrid | `0.7015` | `0.7169` | `0.8034` |
| OpenAI Embedding | `0.5938` | `0.6112` | `0.6765` |

| 비교 | 개선치 |
| --- | --- |
| Hybrid - BM25 | `nDCG@5 +0.0533`, `Recall@5 +0.0545`, `MRR@5 +0.0613` |
| BM25 - OpenAI Embedding | `nDCG@5 +0.0544`, `Recall@5 +0.0512`, `MRR@5 +0.0656` |
| Hybrid - OpenAI Embedding | `nDCG@5 +0.1077`, `Recall@5 +0.1057`, `MRR@5 +0.1269` |

### 6.4 최종 LLM 응답 평가

최종 응답 품질은 단순 문장 생성이 아니라, 근거 기반 설명과 추천 적합성을 함께 평가했습니다.

| 지표 | Mean | 95% CI |
| --- | ---: | --- |
| Evidence | `88.42` | `[85.91, 90.76]` |
| Recommendation | `90.67` | `[88.05, 93.02]` |
| Overall | `89.21` | `[86.97, 91.24]` |
| Pass Rate | `83.3%` | `-` |

| 판정 항목 | 값 |
| --- | ---: |
| threshold profile | `balanced` |
| sample 수 | `12 / 12` |
| 통과 건수 | `10` |
| 실패 건수 | `2` |
| 실패율 | `16.7%` |

### 6.5 E2E 운영 성능

Job Polling 기준 E2E 운영 성능을 측정했습니다.

| 항목 | 결과 |
| --- | ---: |
| accept latency 평균 | `178.62ms` |
| accept latency p95 | `212.47ms` |
| e2e latency 평균 | `4826.35ms` |
| e2e latency p95 | `7314.88ms` |
| system success rate | `1.0` |
| failed count | `0 / 20` |
| 메모리 지표 수집 | `available = true` |

이 결과는 `워밍업 2건`, `본측정 20건`, `동시성 2` 조건에서 측정한 값입니다.

## 7. 트러블슈팅

### 7.1 Netlify 504와 장시간 동기 응답 문제

| 항목 | 내용 |
| --- | --- |
| 문제 | 프론트에서 검색 요청 시 간헐적으로 `504`가 발생하고, 장시간 대기 후 실패하는 문제가 있었습니다. |
| 원인 | 동기 `/query` 요청 한 건이 오래 걸리면 상위 프록시 타임아웃과 충돌했고, 동시성 1 환경에서는 후속 요청이 `429 busy`로 전이됐습니다. |
| 해결 | `/query/jobs` + `/query/jobs/{job_id}` 기반 Job Polling API를 도입하고, 진행 단계를 `queued / running / done / failed`와 `analyzing ~ writing`으로 노출했습니다. |
| 결과 | 장시간 동기 연결에 의존하지 않고 검색 상태를 점진적으로 조회할 수 있게 되었고, 프론트와의 연동 안정성이 좋아졌습니다. |

### 7.2 requests-only 크롤링 회귀와 `view-ajax` 전환

| 항목 | 내용 |
| --- | --- |
| 문제 | 브라우저 의존을 줄이기 위해 raw HTML 기반 수집으로 단순화했을 때, 상세 공고 핵심 정보가 비어 수집 0건 회귀가 발생했습니다. |
| 원인 | 사람인 상세 공고는 raw HTML만으로는 필요한 섹션이 안정적으로 노출되지 않았습니다. |
| 해결 | 상세 공고 수집 경로를 `view-ajax` 기반 병렬 수집으로 전환하고, iframe fallback과 제목 필터링을 적용했습니다. |
| 결과 | 브라우저 전체 렌더링보다 가볍게 운영하면서도 실제 공고 정보 수집 정확도를 유지할 수 있었습니다. |

### 7.3 OOM과 메모리 피크 대응

| 항목 | 내용 |
| --- | --- |
| 문제 | 장시간 요청과 크롤링/파싱/검색이 한 번에 몰리면 메모리 피크와 응답 지연 위험이 커졌습니다. |
| 원인 | 요청당 수집 건수, 검색 상위 개수, 무거운 import, 중간 대용량 리스트가 동시에 메모리를 점유했습니다. |
| 해결 | semaphore 기반 동시성 제한, `max_jobs`/`retrieval_top_k` 상한, 단계별 메모리 로그, 파싱/검색 이후 중간 리스트 해제, 지연 로딩을 적용했습니다. |
| 결과 | 요청당 작업량을 통제하고 병목 지점을 관측할 수 있는 운영 구조를 갖췄습니다. |

### 7.4 배포 이미지 드리프트와 롤아웃 일관성 문제

| 항목 | 내용 |
| --- | --- |
| 문제 | 이미지를 빌드해 푸시하는 것만으로는 VM에서 실제 어떤 이미지가 실행 중인지 보장하기 어려웠습니다. |
| 원인 | `latest` 태그만 갱신하고 실행 이미지 정리와 검증이 없으면, 배포 상태가 불명확해질 수 있었습니다. |
| 해결 | Cloud Build에서 VM 재시작, 실행 이미지와 `latest` 일치 검증, Artifact Registry digest 정리, VM 로컬 앱 이미지 정리 단계를 추가했습니다. |
| 결과 | 배포 후 실제 실행 중인 이미지와 저장소 상태를 일관되게 맞출 수 있게 되었고, 롤아웃 확인 절차가 단순해졌습니다. |

## 8. 배포 구조

### 전체 구성

- 프론트엔드: Netlify 배포
- 백엔드: Docker 컨테이너 기반 FastAPI 서버
- 인프라: GCP VM + Nginx + systemd
- CI/CD: Cloud Build

### 배포 흐름

`main push -> Cloud Build trigger -> Docker image build -> Artifact Registry push -> VM rollout -> AR/VM image cleanup -> health check`

### 백엔드 운영 방식

- 백엔드는 GCP VM 내부에서 Docker 컨테이너로 실행됩니다.
- 외부 요청은 Nginx가 HTTPS로 받아 내부 FastAPI로 프록시합니다.
- systemd가 서비스 재시작 시 최신 이미지를 pull하고 컨테이너를 교체합니다.
- Cloud Build는 이미지 업로드뿐 아니라 VM 재시작과 이미지 정리까지 자동화합니다.

### 왜 이런 구조를 선택했는가

- 프론트와 백엔드를 분리해 각각의 배포 속도와 책임을 분리했습니다.
- 컨테이너 기반으로 로컬과 운영 환경 차이를 줄였습니다.
- Cloud Build와 VM 롤아웃을 연결해 수동 배포 실수를 줄였습니다.
- 이미지 정리 검증까지 자동화해 `배포는 됐는데 실제 반영은 안 된 상태`를 방지했습니다.

## 9. 데모 링크

### 프론트엔드 데모

- [https://job-search-ai.netlify.app/](https://job-search-ai.netlify.app/)

### 샘플 질의

- `서울 백엔드 신입 대졸 채용공고 찾아줘`
- `경기 데이터 분석 3년차 석사 채용공고 추천해줘`
- `서울 AI 엔지니어 신입 고졸 채용공고 찾아줘`
- `서울 프론트엔드 경력 3년차 대졸 공고 보여줘`
- `백엔드 신입 채용공고 찾아줘`

### 사용 시 참고

- 검색 결과는 공고 수집, 파싱, 검색, 응답 생성을 순차적으로 거치므로 수 초의 응답 시간이 발생할 수 있습니다.
- 비동기 Job Polling 구조를 사용하기 때문에, 긴 검색 요청도 진행 상태를 확인하며 처리할 수 있습니다.

## 10. 향후 개선 계획

- `지역` canonicalization을 더 정교하게 개선해 NER 문장 Exact Match를 높이기
- 검색 평가용 judged dataset을 확대해 retrieval 지표의 신뢰도를 높이기
- 최종 LLM 평가 결과와 E2E 결과를 자동으로 산출·보관하는 리포트 파이프라인 추가
- Job 결과 저장소를 메모리 기반에서 영속 저장소 기반으로 확장하기
- 인증, 모니터링, 알림 체계를 추가해 운영 안정성 강화하기
- README용 GIF, 화면 스크린샷, 평가 리포트 시각화를 추가해 첫인상 강화하기

## 참고 메모

- 이 README는 현재 `develop` 기준의 활성 코드 경로와 운영 구조를 설명합니다.
- 백엔드 실 URL은 보안상 공개하지 않았습니다.
- 성능 수치 중 NER는 저장소 내 평가 결과를 기준으로 작성했고, 나머지 지표는 최신 평가 결과 정리본을 기준으로 반영했습니다.
