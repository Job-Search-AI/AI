# Retrieval 디렉토리 하위 파일 분석 보고서

## 개요
`/content/drive/MyDrive/ai_enginner/job_search/AI/src/retrieval` 디렉토리는 채용 검색 시스템의 핵심 검색 기능을 담당하는 모듈입니다. 이 모듈은 쿼리 전처리, 키워드 검색, 임베딩 기반 검색, 그리고 이들을 결합한 하이브리드 검색을 제공합니다.

## 디렉토리 구조
- `__init__.py` (466 bytes): 모듈 초기화 파일
- `__pycache__/`: Python 캐시 디렉토리
- `bm25_retriever.py` (8692 bytes): BM25 키워드 검색 구현
- `data/`: 검색 관련 데이터 파일들 (3개 파일)
- `hybrid_retriever.py` (12159 bytes): 하이브리드 검색 시스템
- `query_config.py` (1153 bytes): 쿼리 처리 설정
- `query_processor.py` (8853 bytes): 쿼리 전처리 및 확장
- `test_hybrid_retrieval.py` (8069 bytes): 테스트 및 평가 스크립트

## 파일별 상세 분석

### 1. `__init__.py`
**용도**: 검색 모듈의 공개 인터페이스 정의
- 주요 클래스: `QueryProcessor`, `BM25Retriever`, `HybridRetriever`를 import 및 공개
- 문서화: 모듈의 주요 기능 설명 (쿼리 전처리, BM25 검색, 임베딩 검색, 하이브리드 검색, 재순위화)

### 2. `bm25_retriever.py`
**용도**: BM25 알고리즘 기반 키워드 검색 구현
- 주요 기능:
  - 텍스트 토크나이징 (KoNLPy 사용 또는 간단한 공백 분리)
  - 문서 컬렉션 인덱싱 (용어 빈도, 문서 빈도, IDF 계산)
  - BM25 점수 계산 및 검색
  - 인덱스 저장/로드 기능
- 매개변수: k1 (용어 빈도 포화), b (문서 길이 정규화)
- 특징: 한국어 형태소 분석 지원

### 3. `hybrid_retriever.py`
**용도**: BM25와 임베딩 검색을 결합한 하이브리드 검색 시스템
- 주요 기능:
  - BM25와 임베딩 모델 통합
  - 쿼리 확장 및 전처리
  - 점수 결합 방법: 가중 평균, RRF (Reciprocal Rank Fusion)
  - 검색 결과 정규화 및 재순위화
- 특징: 동적 가중치 조정, 구성 요소별 결과 분석 기능

### 4. `query_config.py`
**용도**: 쿼리 처리 관련 설정 관리
- 설정 카테고리:
  - 동의어 확장 설정
  - 지역명 정규화 설정
  - 학력 표준화 설정
  - 직무 카테고리 설정
  - 쿼리 전처리 설정
  - 확장 가중치 설정

### 5. `query_processor.py`
**용도**: 쿼리 전처리 및 확장 담당
- 주요 클래스:
  - `QueryProcessor`: 메인 쿼리 처리 클래스
  - `SynonymExpander`: 동의어 확장
  - `LocationNormalizer`: 지역명 정규화
  - `EducationNormalizer`: 학력 정규화
- 기능: 데이터 파일 로드, 쿼리 확장, 문자열 변환

### 6. `test_hybrid_retrieval.py`
**용도**: 하이브리드 검색 시스템의 테스트 및 성능 평가
- 주요 기능:
  - 성능 메트릭 계산 (Recall@k, Precision@k, Hit@k)
  - 검색 방법 비교 (BM25 vs 임베딩 vs 하이브리드)
  - 평가 데이터셋 로드 및 처리
- 특징: GPU 메모리 관리, 상세한 디버깅 정보 출력

### 7. `data/` 서브디렉토리
- `education.json`: 학력 관련 표준화 데이터
- `locations.json`: 지역 관련 표준화 데이터
- `synonyms.json`: 동의어 사전

## 파일 간 관계 및 의존성

### 의존성 그래프
```
test_hybrid_retrieval.py
    ↓
hybrid_retriever.py
    ↓
bm25_retriever.py
query_processor.py
    ↓
query_config.py
    ↓
data/*.json
```

### 주요 관계
- `hybrid_retriever.py`: `bm25_retriever.py`, `query_processor.py`를 내부적으로 사용
- `query_processor.py`: `query_config.py`의 설정을 사용하며 `data/`의 JSON 파일들을 로드
- `test_hybrid_retrieval.py`: 전체 시스템을 테스트하는 통합 스크립트

## 기술 스택
- **프로그래밍 언어**: Python
- **주요 라이브러리**: 
  - BM25 계산: 내장 수학 함수
  - 한국어 처리: KoNLPy (선택적)
  - 임베딩: 외부 모델 (프로젝트 내 `src.embedding.model`)
  - 평가: `src.evaluation.retrieval.metrics`
- **데이터 형식**: JSON, JSONL
- **저장 형식**: Pickle (인덱스 저장용)

## 결론
이 retrieval 모듈은 채용 검색 시스템의 핵심 검색 기능을 제공하며, 다음과 같은 특징을 가집니다:

1. **유연성**: BM25, 임베딩, 하이브리드 검색 방법을 지원
2. **확장성**: 쿼리 확장 및 정규화를 통해 다양한 검색 패턴 지원
3. **성능 최적화**: 인덱스 저장/로드, 점수 정규화 등
4. **테스트 가능성**: 포괄적인 테스트 및 평가 기능 포함

추가 개선 사항으로 고려할 수 있는 부분:
- 더 정교한 한국어 토크나이징
- 실시간 인덱스 업데이트
- 분산 검색 지원
- 캐싱 메커니즘 강화

이 분석을 통해 프로젝트의 검색 아키텍처를 이해하고, 향후 개발 방향을 설정할 수 있습니다.
