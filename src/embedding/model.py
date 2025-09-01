from sentence_transformers import SentenceTransformer
from ..utils import get_device, print_device_info

def similarity_docs_retrieval(query, documents, device_preference="auto"):
    """
    문서 유사도 검색 함수
    
    Args:
        query (str): 검색 쿼리
        documents (list): 검색할 문서 리스트
        device_preference (str): "auto", "cuda", "mps", "cpu" 중 선택
        
    Returns:
        list: 문서와 유사도 점수 쌍의 리스트
    """
    # device 선택
    device = get_device(device_preference)
    print_device_info(device)
    
    # 모델 로드
    model_name = 'dragonkue/snowflake-arctic-embed-l-v2.0-ko'
    
    # device에 따른 설정
    if device == "cuda":
        model = SentenceTransformer(model_name, device=device)
    elif device == "mps":
        # MPS의 경우 CPU로 로드 후 MPS로 이동
        model = SentenceTransformer(model_name, device="cpu")
        model = model.to(device)
    else:
        model = SentenceTransformer(model_name, device="cpu")

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
        print(f"{score:.4f}: {document[:100]}...")

    return doc_score_pairs

if __name__ == '__main__':
    query = "웹 개발자 신입 채용"
    documents = [
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

    print("=== Device 선택 예시 ===")
    print("1. 자동 선택 (권장)")
    doc_score_pairs = similarity_docs_retrieval(query, documents, "auto")
    print('doc_score_pairs: ', doc_score_pairs)
    
    print("\n2. CPU 강제 사용")
    doc_score_pairs = similarity_docs_retrieval(query, documents, "cpu")
    print('doc_score_pairs: ', doc_score_pairs)