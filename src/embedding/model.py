import torch
import os
import sys
# python -m src.embedding.model

# 이 파일을 단독으로 실행시킬시 아래의 두 주석을 풀고 실행시켜야 캐쉬저장된다.
# cache_dir = '/content/drive/MyDrive/ai_enginner/job_search/AI/cache/'
# os.environ['HF_HOME'] = cache_dir
sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")

from sentence_transformers import SentenceTransformer
from src.utils import dict_to_str
from src.utils.device_selector import get_device, print_device_info

# 모델 캐시를 위한 전역 변수
_model_cache = None

def get_model():
    global _model_cache
    if _model_cache is None:
        device = get_device()
        print_device_info(device)
        print('모델 로드 시작')
        model_name = 'dragonkue/snowflake-arctic-embed-l-v2.0-ko'
        _model_cache = SentenceTransformer(model_name).to(device)
        print('모델 로드 완료')
    return _model_cache

def similarity_docs_retrieval(query, documents, precomputed_doc_embeddings=None):
    """
    문서 유사도 검색 함수
    
    Args:
        query (str): 검색 쿼리
        documents (list:str or list:dict): 검색할 문서 리스트 (문자열 리스트 또는 딕셔너리 리스트)
        precomputed_doc_embeddings (torch.Tensor, optional): 미리 계산된 문서 임베딩
        
    Returns:
        res_documents: 유사도 검색된 문서 리스트
        res_scores: 유사도 검색된 문서의 유사도 점수 리스트

    """

    print('-'*10, '유사도 검색 시작', '-'*10)
    
    model = get_model()

    print('documents를 문자열로 변환 시작')
    documents_for_embedding = dict_to_str(documents)
    print('documents를 문자열로 변환 완료')

    # 임베딩 계산
    print('임베딩 계산 시작')
    query_embeddings = model.encode(query, prompt_name="query")
    
    if precomputed_doc_embeddings is not None:
        document_embeddings = precomputed_doc_embeddings
        print('미리 계산된 문서 임베딩 사용')
    else:
        document_embeddings = model.encode(documents_for_embedding, batch_size=2)
    print('임베딩 계산 완료')

    # 코사인 유사도 점수 계산
    print('코사인 유사도 점수 계산 시작')
    scores = model.similarity(query_embeddings, document_embeddings)
    print('코사인 유사도 점수 계산 완료')

    # 문서와 유사도 점수 쌍 생성 및 정렬
    print('문서와 유사도 점수 쌍 생성 및 정렬 시작')
    doc_score_pairs = list(zip(documents_for_embedding, scores[0]))
    doc_score_pairs = sorted(doc_score_pairs, key=lambda x: x[1], reverse=True)
    print('문서와 유사도 점수 쌍 생성 및 정렬 완료')

    res_documents = []
    res_scores = []
    print('문서와 유사도 점수 쌍 출력 시작')
    for document, score in doc_score_pairs:
        res_documents.append(document)
        res_scores.append(score)
        print(f"{score:.4f}: {document[:100]}...")
    print('문서와 유사도 점수 쌍 출력 완료')

    return res_documents, res_scores

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

    doc_score_pairs = similarity_docs_retrieval(query, documents)
