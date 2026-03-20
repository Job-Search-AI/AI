# 문제 요약

`main` 푸시 후 Cloud Build 자체는 성공했지만, GCP 트리거 `ai-main-build`가 리포의 `cloudbuild.yaml`이 아니라 GCP에 저장된 인라인 빌드 설정을 사용하고 있다. 그 결과 README에 정의된 Artifact Registry 정리와 VM 앱 이미지 정리 단계가 실행되지 않았다.

# 영향 범위(서비스/사용자/기능)

- `main` 푸시 기반 배포는 정상적으로 빌드, 이미지 푸시, VM 재시작까지 수행된다.
- Artifact Registry 고유 digest 수가 `1`로 유지되지 않고 누적된다.
- VM 로컬 앱 이미지 수도 `1`로 유지되지 않고 누적된다.
- 운영 문서 `GCP.README.md`와 실제 배포 파이프라인이 불일치한다.

# 재현 조건

1. `main` 브랜치에 커밋을 푸시한다.
2. Cloud Build 트리거 `ai-main-build`가 실행된다.
3. 빌드 완료 후 `gcloud builds describe <BUILD_ID> --region=us-central1 --format=yaml`로 스텝을 확인한다.
4. 스텝이 `Build image`, `Push image (build id)`, `Push image (latest)`, `Rollout VM (restart service)` 4개만 보인다.
5. Artifact Registry digest 수와 VM 앱 이미지 수를 조회하면 각각 `2`가 나온다.

# 가설 목록

- 트리거 생성 당시 인라인 빌드 설정이 저장됐고 이후 리포 `cloudbuild.yaml` 변경이 트리거에 반영되지 않았다.
- 현재 트리거는 `filename` 기반이 아니라 `build:` 인라인 템플릿 기반으로 동작한다.
- 운영 문서는 파일 기반 파이프라인을 기준으로 작성됐지만 실제 트리거 설정은 업데이트되지 않았다.

# 시도 기록(시간, 조치, 결과)

- 2026-03-20 18:42 KST: `main`에 머지 커밋 `4c9893e1fb3ad25d71a036ba72d826117e1699a2` 푸시. Cloud Build `ee95b339-f598-4d31-84a8-9f3191849b5d` 시작 확인.
- 2026-03-20 18:47 KST: `gcloud builds describe ee95b339-f598-4d31-84a8-9f3191849b5d --region=us-central1` 결과 `SUCCESS` 확인. 실행 스텝은 4개만 존재.
- 2026-03-20 18:48 KST: Artifact Registry 조회 결과 최신 digest `sha256:583757374e6f580e7595fcda84548f220a20d1bee88dc94c2254e2f0bf076c73`, 고유 digest 수 `2` 확인.
- 2026-03-20 18:48 KST: VM `jobsearch-api`는 `active`, `container_image_id`와 `latest_id`는 일치, VM 앱 이미지 수는 `2` 확인.
- 2026-03-20 18:49 KST: `gcloud builds triggers describe 0de8fbd2-616a-4d52-83bb-fd70cf6d50ff --region=us-central1 --format=yaml` 결과 트리거가 `filename` 없이 `build:` 인라인 설정을 사용 중임을 확인.
- 2026-03-20 18:56 KST: 사용자 요청으로 최신 `latest` 기준 외의 Artifact Registry digest를 수동 삭제. 고유 digest 수 `1` 확인.
- 2026-03-20 18:57 KST: 사용자 요청으로 VM에서 실행 중 이미지 외의 로컬 앱 이미지를 수동 삭제. `jobsearch-api active`, `container_image_id == latest_id`, VM 앱 이미지 수 `1` 확인.

# 실패 원인 분석

배포 실패는 아니다. 다만 Cloud Build 트리거가 리포 `cloudbuild.yaml`을 읽지 않고, GCP 트리거 내부에 저장된 오래된 4단계 인라인 빌드 설정을 사용한다. 그래서 cleanup 단계가 구조적으로 실행될 수 없다.

# 의사결정 근거

- 서비스 가용성은 유지되고 `/health`, `/query/jobs` 동작도 정상이라 즉시 장애 상황은 아니다.
- 하지만 운영 문서와 실제 트리거 설정이 불일치하고, 이미지 정리 정책이 미적용 상태라 장기적으로 운영 부채가 쌓인다.
- 이는 코드 수정이 아니라 GCP 트리거 설정 변경이 필요할 가능성이 높아, 사용자 확인 없이 바로 인프라 설정을 바꾸지 않는다.

# 최종 결정 및 다음 액션

- 현재 배포 결과와 파이프라인 불일치 원인을 사용자에게 보고한다.
- 사용자 요청에 따라 최신 digest 1개와 VM 앱 이미지 1개만 남도록 수동 정리를 수행했다.
- 사용자가 승인하면 트리거를 리포 `cloudbuild.yaml` 기반으로 전환하거나, 동일한 cleanup 스텝을 트리거 인라인 설정에 반영한다.
- 수정 후 `main` 재배포를 실행하고 digest 수와 VM 앱 이미지 수가 모두 `1`인지 다시 검증한다.

# 후속 조치 및 해결 결과

- 2026-03-20 21:57 KST: 사용자 승인 후 `gcloud builds triggers import --region=us-central1`로 트리거 `ai-main-build`를 재적용해 `filename: cloudbuild.yaml` 기반으로 전환했다.
- 2026-03-20 21:58 KST: `gcloud builds triggers describe 0de8fbd2-616a-4d52-83bb-fd70cf6d50ff --region=us-central1 --format=yaml` 재확인 결과 `build:` 인라인 블록은 사라지고 `filename: cloudbuild.yaml`만 남았다.
- 현재 기준으로 트리거 설정 불일치 문제는 해소됐다.
- 다만 리포의 `cloudbuild.yaml`은 정리 단계가 제거된 4단계 배포 기준이므로, main 배포 이후 Artifact Registry digest와 VM 로컬 앱 이미지는 운영자가 최신 1개만 남도록 수동 정리해야 한다.
