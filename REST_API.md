# REST API 명세서

기준 코드: `api/main.py`, `src/state/slices/url_exchanger.py`

## 1. 개요

- Base URL: `http://localhost:8000`
- Content-Type: `application/json`
- 인증: 없음
- CORS: 모든 Origin 허용
- 자동 문서:
  - `GET /docs`
  - `GET /openapi.json`

## 2. 공통 규칙

- 요청 본문은 정의된 필드만 허용한다.
- 정의되지 않은 필드를 보내면 `422 Unprocessable Entity`가 반환된다.
- 응답의 선택 필드는 값이 없으면 `null`로 반환된다.
- `/query`는 내부적으로 `query` 기본값을 `user_input`과 동일하게 사용한다.
- `/query`는 내부적으로 검색 개수 기본값을 `5`로 사용한다.

## 3. 엔드포인트

### 3.1 `GET /health`

서버 상태 확인용 엔드포인트다.

#### 요청

- Body 없음

#### 응답

`200 OK`

```json
{
  "status": "ok"
}
```

#### curl 예시

```bash
curl -s http://localhost:8000/health
```

---

### 3.2 `POST /query`

자연어 채용 검색 요청을 받아 엔티티 추출, 정규화, URL 생성, 크롤링, 검색, 응답 생성을 수행한다.

#### 요청 헤더

```http
Content-Type: application/json
```

#### 요청 본문

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `user_input` | `string` | Y | 사용자의 자연어 검색 문장 |

#### 요청 예시

```json
{
  "user_input": "서울 AI 엔지니어 신입 고졸 채용공고 찾아줘."
}
```

#### 응답 필드

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `user_input` | `string` | Y | 원본 사용자 입력 |
| `query` | `string` | Y | 실제 검색 질의 |
| `status` | `string` | Y | `complete` 또는 `incomplete` |
| `message` | `string \| null` | N | 추가 안내 문구 |
| `entities` | `object \| null` | N | 원본 엔티티 추출 결과 |
| `entities.지역` | `string` | N | 추출된 지역 |
| `entities.직무` | `string` | N | 추출된 직무 |
| `entities.경력` | `string` | N | 추출된 경력 |
| `entities.학력` | `string` | N | 추출된 학력 |
| `지역` | `string \| null` | N | 상태에 저장된 지역 값 |
| `직무` | `string \| null` | N | 상태에 저장된 직무 값 |
| `경력` | `string \| null` | N | 상태에 저장된 경력 값 |
| `학력` | `string \| null` | N | 상태에 저장된 학력 값 |
| `missing_fields` | `string[] \| null` | N | 누락된 필수 슬롯 목록 |
| `normalized_entities` | `object \| null` | N | 정규화된 엔티티 |
| `normalized_entities.지역` | `string \| null` | N | 정규화된 지역 |
| `normalized_entities.직무` | `string \| null` | N | 정규화된 직무 |
| `normalized_entities.경력` | `string \| null` | N | 정규화된 경력 |
| `normalized_entities.학력` | `string \| null` | N | 정규화된 학력 |
| `url` | `string \| null` | N | 생성된 사람인 검색 URL |
| `crawled_count` | `integer \| null` | N | 수집한 공고 수 |
| `job_info_list` | `string[] \| null` | N | 파싱된 전체 공고 텍스트 목록 |
| `retrieved_job_info_list` | `string[] \| null` | N | 검색 상위 공고 텍스트 목록 |
| `retrieved_scores` | `number[] \| null` | N | 검색 점수 목록 |
| `user_response` | `string \| null` | N | 최종 사용자 응답 문장 |

#### 상태값 의미

| `status` | 설명 |
| --- | --- |
| `incomplete` | 필수 슬롯(`지역`, `직무`, `경력`, `학력`)이 부족해서 검색을 중단한 상태 |
| `complete` | 검색과 응답 생성까지 완료한 상태 |

#### 성공 응답 예시 1: 정보 부족

`200 OK`

```json
{
  "user_input": "백엔드 신입 채용공고 찾아줘",
  "query": "백엔드 신입 채용공고 찾아줘",
  "status": "incomplete",
  "message": "지역, 학력 정보를 알려주세요.",
  "entities": {
    "지역": "",
    "직무": "백엔드",
    "경력": "신입",
    "학력": ""
  },
  "지역": "",
  "직무": "백엔드",
  "경력": "신입",
  "학력": "",
  "missing_fields": [
    "지역",
    "학력"
  ],
  "normalized_entities": {
    "지역": null,
    "직무": "백엔드/서버개발",
    "경력": "신입",
    "학력": null
  },
  "url": null,
  "crawled_count": null,
  "job_info_list": null,
  "retrieved_job_info_list": null,
  "retrieved_scores": null,
  "user_response": null
}
```

#### 성공 응답 예시 2: 검색 완료

`200 OK`

```json
{
  "user_input": "서울 AI 엔지니어 신입 고졸 채용공고 찾아줘.",
  "query": "서울 AI 엔지니어 신입 고졸 채용공고 찾아줘.",
  "status": "complete",
  "message": null,
  "entities": {
    "지역": "서울",
    "직무": "AI 엔지니어",
    "경력": "신입",
    "학력": "고졸"
  },
  "지역": "서울",
  "직무": "AI 엔지니어",
  "경력": "신입",
  "학력": "고졸",
  "missing_fields": null,
  "normalized_entities": {
    "지역": "서울",
    "직무": "인공지능/머신러닝",
    "경력": "신입",
    "학력": "고등학교졸업이상"
  },
  "url": "https://www.saramin.co.kr/zf_user/search?...",
  "crawled_count": 12,
  "job_info_list": [
    "********** ... 전체 공고 텍스트 ..."
  ],
  "retrieved_job_info_list": [
    "********** ... 상위 공고 텍스트 ..."
  ],
  "retrieved_scores": [
    0.91,
    0.87,
    0.82,
    0.79,
    0.75
  ],
  "user_response": "서울 지역 신입 AI 엔지니어 채용공고를 우선순위로 정리하면 다음과 같습니다..."
}
```

#### 검증 오류 예시

`422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": [
        "body",
        "user_input"
      ],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

#### curl 예시

```bash
curl -sS -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"user_input":"서울 AI 엔지니어 신입 고졸 채용공고 찾아줘."}'
```

---

### 3.3 `POST /query/jobs`

검색 작업을 비동기로 접수한다. 요청은 즉시 큐에 적재되고 `jobId`를 반환한다.

#### 요청 헤더

```http
Content-Type: application/json
```

#### 요청 본문

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `user_input` | `string` | Y | 사용자의 자연어 검색 문장 |

#### 성공 응답

`202 Accepted`

```json
{
  "jobId": "abc123",
  "status": "queued"
}
```

#### 검증 오류 예시

`422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": ["body", "user_input"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

#### curl 예시

```bash
curl -sS -X POST http://localhost:8000/query/jobs \
  -H "Content-Type: application/json" \
  -d '{"user_input":"서울 백엔드 신입 대졸 채용공고 찾아줘"}'
```

---

### 3.4 `GET /query/jobs/{jobId}`

비동기 검색 작업 상태를 조회한다.

#### 상태 전이

`queued -> running -> done | failed`

#### 성공 응답 예시 1: 대기/실행중

`200 OK`

```json
{
  "jobId": "abc123",
  "status": "running"
}
```

#### 성공 응답 예시 2: 완료

`200 OK`

```json
{
  "jobId": "abc123",
  "status": "done",
  "result": {
    "user_input": "서울 백엔드 신입 대졸 채용공고 찾아줘",
    "query": "서울 백엔드 신입 대졸 채용공고 찾아줘",
    "status": "complete",
    "message": null
  }
}
```

#### 성공 응답 예시 3: 실패

`200 OK`

```json
{
  "jobId": "abc123",
  "status": "failed",
  "message": "job failed"
}
```

#### 없는 작업 ID

`404 Not Found`

```json
{
  "message": "job not found"
}
```

#### curl 예시

```bash
curl -sS http://localhost:8000/query/jobs/abc123
```

## 4. 문서 경로

| 경로 | 설명 |
| --- | --- |
| `GET /docs` | Swagger UI |
| `GET /openapi.json` | OpenAPI JSON |
