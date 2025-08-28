from sentence_transformers import SentenceTransformer
import sys
sys.path.insert(0, "/content/drive/MyDrive/ai_enginner/job_search/AI/")
sys.path.insert(0, "/content/drive/MyDrive/package")

def similarity_docs_retrieval(query, documents):
    # 모델 로드
    model_name = 'dragonkue/snowflake-arctic-embed-l-v2.0-ko'
    model = SentenceTransformer(model_name)

    # 임베딩 계산
    query_embeddings = model.encode(query, prompt_name="query")
    document_embeddings = model.encode(documents)

    # 코사인 유사도 점수 계산
    scores = model.similarity(query_embeddings, document_embeddings)
    
    # 문서와 유사도 점수 쌍 생성 및 정렬
    doc_score_pairs = list(zip(documents, scores[0]))
    doc_score_pairs = sorted(doc_score_pairs, key=lambda x: x[1], reverse=True)
    print("Query:", query)
    for document, score in doc_score_pairs:
            print(score, document)

    return doc_score_pairs


if __name__ == '__main__':
    query = '프론트엔드,퍼블리셔,반응형웹,웹에이전시등록일 25/08/26'
    documents = [
"""
    제목: 퍼블리셔 신입&경력 채용
    직무: 프론트엔드,퍼블리셔,반응형웹,웹에이전시등록일 25/08/26
    근무지: 서울금천구
    경력: 신입
    학력: 학력무관
    마감일: ~ 09/25(목)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51657724&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
"""
제목: [캐시워크] 프론트엔드개발 채용전환형 인턴
    직무: 프론트엔드,웹개발,React,앱개발,유지보수외등록일 25/08/06
    근무지: 서울강남구
    경력: 신입
    학력: 학력무관
    마감일: ~ 10/05(일)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51490873&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
"""
    제목: [캐시워크] iOS개발 채용전환형 인턴
    직무: 프론트엔드,웹개발,앱개발,유지보수,Flutter외등록일 25/08/06
    근무지: 서울강남구
    경력: 신입
    학력: 학력무관
    마감일: ~ 10/05(일)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51490868&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
"""
    제목: 프론트엔드 개발 신입 모집
    직무: 프론트엔드,React,CSS,소프트웨어개발수정일 25/08/08
    근무지: 서울전체
    경력: 신입
    학력: 고졸↑
    마감일: ~ 09/04(목)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51488165&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
"""
    제목: [캐시워크] 안드로이드개발 채용전환형 인턴
    직무: 프론트엔드,앱개발,유지보수,기술지원,데이터분석가외등록일 25/07/14
    근무지: 서울강남구
    경력: 신입
    학력: 학력무관
    마감일: ~ 09/12(금)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51290346&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
"""
    제목: [캐시워크] Flutter개발 채용전환형 인턴
    직무: 프론트엔드,웹개발,앱개발,유지보수,웹마스터외등록일 25/07/14
    근무지: 서울강남구
    경력: 신입
    학력: 학력무관
    마감일: ~ 09/12(금)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51290303&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
"""
    제목: [엔키화이트햇] 개발팀 : Backend 개발자 인턴
    직무: 프론트엔드,백엔드/서버개발,웹개발,기술지원,API외등록일 25/07/10
    근무지: 서울전체
    경력: 신입
    학력: 학력무관
    마감일: ~ 08/31(일)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51266854&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
"""
    제목: 웹/서버 SW 신입 - Devops 솔루션 서비스 운영 파트
    직무: 프론트엔드,백엔드/서버개발,웹개발,Java,Python외등록일 25/08/20
    근무지: 서울성동구
    경력: 신입
    학력: 학력무관
    마감일: ~ 09/19(금)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51607414&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
"""
    제목: 웹/서버 SW 백엔드 개발자 신입 (Legal Startup)
    직무: 프론트엔드,백엔드/서버개발,웹개발,Java,Python외등록일 25/08/20
    근무지: 서울성동구
    경력: 신입
    학력: 학력무관
    마감일: ~ 09/19(금)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51607397&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
"""
    제목: 산업기능요원 정보처리 채용 [보충역]개발 PHP,node.js,병역특례
    직무: 프론트엔드,웹개발,Java,PHP,모바일디자인외등록일 25/08/18
    근무지: 서울마포구
    경력: 신입
    학력: 학력무관
    마감일: ~ 09/17(수)
    지원링크: https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=search&rec_idx=51583350&location=ts&searchType=search&paid_fl=n&search_uuid=890abe52-472d-47a4-a0f0-9e2c508da12c
""",
    ]

    doc_score_pairs =similarity_docs_retrieval(query, documents)
    print('doc_score_pairs: ', doc_score_pairs)