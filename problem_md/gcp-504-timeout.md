# 1. 문제 요약

- 2026-03-13(KST) 기준, `https://job-search-ai.netlify.app/api/query` 호출 시 간헐적으로 `504`가 발생한다.
- 프런트(Netlify)에서는 `{"message":"Backend API request timed out after 12s."}`가 반복 관측되었다.
- GCP VM 백엔드 직접 호출(`https://35-206-120-191.sslip.io/query`)은 `200`이 나오기도 하지만, 처리시간이 `98.89s`까지 길어지고 동시 요청은 `45s` 후 `429 busy`로 떨어진다.

# 2. 영향 범위(서비스/사용자/기능)

- 서비스: 검색 API 응답 안정성 저하(간헐 실패, 장시간 지연).
- 사용자: 검색 버튼 클릭 후 실패 배지/재시도 루프 경험, 신뢰도 저하.
- 기능: `/query` 기반 메인 검색 플로우 전체 영향.

# 3. 재현 조건

- Netlify 경유:
  - `POST https://job-search-ai.netlify.app/api/query`
  - 본문 예시: `{"user_input":"서울 백엔드 신입 대졸 채용공고 찾아줘"}`
  - 결과: 약 12~14초 후 `504`, 메시지에 `timed out after 12s`.
- GCP 직접:
  - `POST https://35-206-120-191.sslip.io/query`
  - 동일 본문
  - 결과: `200`이지만 `98.89s`, 이후 요청은 `45s` 후 `429 busy` 재현.

# 4. 가설 목록

1. Netlify API 프록시/함수 타임아웃(12초)이 백엔드 장시간 처리와 충돌해 504 발생.
2. GCP 백엔드 처리 자체가 느려 요청이 12초를 넘기며 상위 프록시에서 먼저 종료됨.
3. `QUERY_CONCURRENCY=1` 설정으로 단일 장기 요청이 전체 요청을 막아 연쇄 실패 유발.
4. 배포 이미지가 로컬 최신 코드와 불일치(구버전 크롤러 사용)하여 처리시간이 악화.

# 5. 시도 기록(시간, 조치, 결과)

- 2026-03-13 23:20~23:24 KST
  - 조치: GCP 직접 `/query` 반복 호출.
  - 결과:
    - 1회차 `200`, `total=98.891759s`
    - 2~3회차 `429`, `total=45.xs` (busy timeout과 일치)
    - 4회차 클라이언트 `180s` 타임아웃
- 2026-03-13 23:26~23:27 KST
  - 조치: Netlify `/api/query` 반복 호출.
  - 결과: 4회 모두 `504`, `total=12~14s`, 본문에 `timed out after 12s`.
- 2026-03-13 23:25~23:28 KST
  - 조치: VM 내부 상태 점검(`systemctl`, `journalctl`, `nginx`, `docker exec`).
  - 결과:
    - VM: 2 vCPU/약 2GB 메모리, swap 없음.
    - 앱 로그: Selenium 기반 크롤링 동작, 상세 페이지 순회 로그 다수.
    - Nginx: `proxy_read_timeout 300s`로 VM 프록시 자체는 12초 제한이 아님.
    - 컨테이너 내부 `/app/src/tools/slices/crawling.py`는 Selenium 구현 확인.

# 6. 실패 원인 분석

- 1차 표면 원인:
  - Netlify 경유 요청은 12초 백엔드 대기 제한에 걸려 `504` 반환.
- 2차 근본 원인:
  - GCP 백엔드 `/query` 처리시간이 12초를 크게 초과(실측 98초+).
  - 현재 배포 컨테이너는 Selenium 기반 크롤러를 사용해 페이지별 대기/DOM 상호작용 비용이 큼.
  - API 동시성 제한(`QUERY_CONCURRENCY=1`)으로 장기 요청 1개가 큐를 독점하여 추가 요청이 `429`로 전이.

# 7. 의사결정 근거

- 동일 입력으로 경로별 응답시간이 명확히 구분됨:
  - Netlify 경유: 항상 12초대 504
  - GCP 직접: 98초 200 또는 45초 429
- VM Nginx의 `proxy_read_timeout=300s` 확인으로, VM nginx가 12초 504를 내는 구조가 아님을 배제.
- 컨테이너 내부 코드 확인으로 Selenium 크롤러 사용 사실을 직접 확인.

# 8. 최종 결정 및 다음 액션

- 최종 결정:
  - 이번 504는 "Netlify 12초 제한"과 "백엔드 장기 처리"의 결합 이슈다.
  - GCP VM 단일 원인이라기보다, VM 처리시간이 길어 상위 프록시 타임아웃을 촉발하는 구조다.
- 다음 액션:
  1. 백엔드 최신(비-Selenium) 코드가 포함된 이미지 재빌드/재배포 후 응답시간 재측정.
  2. `QUERY_CONCURRENCY` 및 `QUERY_BUSY_TIMEOUT_SECONDS` 운영값 재설정으로 큐 고착 완화.
  3. Netlify `/api/query` 프록시 타임아웃 정책 상향 또는 SSE/비동기 패턴으로 전환.
  4. `/query` 단계별 소요시간 로그(노드별 latency) 추가로 병목 지점 상시 관측.

# 9. 추가 검증 (2026-03-13 23:40~23:50 KST)

- 목적:
  - Selenium 기반 크롤링 결과와 requests(raw HTML) 기반 크롤링 결과의 실제 수집 데이터 차이를 검증.
- 방법:
  - 동일 검색 URL(`서울/백엔드/신입/4년제대학교`)을 기준으로,
    1) requests로 목록/상세 HTML 수집 후 선택자 존재 여부 확인
    2) Selenium으로 동일 상세 URL 렌더 후 `page_source`에서 동일 선택자 확인
- 결과:
  - 샘플 5개 상세 URL에서
    - requests(raw): `.wrap_jview > section:first-of-type > div.wrap_jv_cont` 존재 0/5
    - requests(raw): `h1.tit_job` 존재 0/5
    - Selenium(rendered): 위 두 선택자 모두 5/5 존재
  - 동일 조건 `max_count=10`에서
    - Selenium 레거시 호환 추출: 10건 수집
    - requests 기반 추출: 0건 수집
- 해석:
  - 사람인 상세 페이지는 JS 렌더 이후에 핵심 DOM이 채워지는 구조로 보이며,
  - 단순 requests(raw HTML)만으로는 현재 선택자 기준 데이터 추출이 실패한다.
  - 즉, Selenium 제거 시 성능은 개선될 수 있어도 정확도/수집률 회귀 위험이 매우 크다.

# 10. 후속 조치 기록 (2026-03-16 KST)

- 조치:
  - 백엔드 Job API 응답을 `job_id + jobId` 병행 형태로 확장.
  - Job 상태에 `step`, `step_label` 필드를 추가해 Polling 기반 진행률 표시에 대응.
  - Job 워커를 그래프 `stream(updates)` 기반으로 변경해 `analyzing -> collecting -> parsing -> ranking -> writing` 단계 갱신 반영.
  - `normalize_entities`에서 `incomplete`인 경우 즉시 `done(result.status=incomplete)` 처리.
  - `JOB_RESULT_TTL_SECONDS` 운영값에 하한(300초)을 적용해 최소 5분 보관 보장.
  - 레거시 `/query/stream` 엔드포인트 및 관련 테스트/문서를 제거해 Polling 경로로 단일화.
  - API 문서를 Job Polling 권장 흐름으로 갱신.
- 결과:
  - `uv run pytest -q tests/test_api.py` 기준 `7 passed`.
  - 검증 항목에 `job_id/jobId` 호환, running 단계 전이, `done(incomplete)`, TTL 하한 동작이 포함됨.
- 다음 액션:
  1. 프론트 `/api/query/start`, `/api/query/status` 프록시를 실제 배포 브랜치에 연결해 종단 간 검증.
  2. 운영 환경에서 Job 상태 조회 트래픽 대비 메모리 사용량(`job_store`) 모니터링.
