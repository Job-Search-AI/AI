from pydantic import BaseModel
from fastapi import FastAPI

from src import (
    crawl_job_html_from_saramin,
    similarity_docs_retrieval,
    generate_response,
    parsing_job_info,
    predict_crf_bert,
    normalize_and_validate_entities,
    keep_loading_job_model,
    mapping_url_query
)

_MODEL_CACHE = {
    "bert_model": None,
    "tokenizer": None,
    "crf": None,
    "device": None,
}

if _MODEL_CACHE["bert_model"] is None:   
    _MODEL_CACHE = keep_loading_job_model(bert_model="klue/bert-base")

# query

# follow up

# 첫 사용자 입력 질문
class Query_Request(BaseModel):
    user_input: str

# 부족한 정보 있을시 재질문
class Follow_Up_Request(BaseModel):
    user_input: str
    prev_entity: dict

app = FastAPI()

@app.post("/query")
def handle_query(request: Query_Request):
    user_input = request.user_input

    # 1. 사용자 입력 NER 인식
    entities = predict_crf_bert(user_input, _MODEL_CACHE["bert_model"], _MODEL_CACHE["crf"], _MODEL_CACHE["tokenizer"], _MODEL_CACHE['device'])

    # 2. 사용자 입력 엔티티 표준화
    # status: 표준화 완성 여부 상태
    # message: 누락정보 재입력 요청 메시지
    # missing_fields: 누락된 항목 리스트
    # normalized_entities: 표준화된 엔티티
    status, message, missing_fields, normalized_entities = normalize_and_validate_entities(entities)

    # 만약 누락된 정보가 있다면, 재질문
    if status == 'incomplete':
        return {
            "status": status,
            "message": message,
            "missing_fields": missing_fields,
            "normalized_entities": normalized_entities
        }
        
    # 3. URL 생성
    url = mapping_url_query(normalized_entities)

    # 4. 사람인 채용 정보 html 추출
    html_contents = crawl_job_html_from_saramin(url, max_jobs)

    # 5. html 파싱
    job_info_list = parsing_job_info(html_contents)

    # 6. 임베딩, 리트리버
    retriever = HybridRetriever(bm25_weight=0.6, embedding_weight=0.4)
    retriever.build_index(job_info_list)

    results, scores = retriever.search(user_input, top_k=5, combination_method="rrf", use_query_expansion=True)

    for rank, (doc, score) in enumerate(zip(results, scores), 1):
        print(f"Rank {rank}: {doc}, score: {score}")
    
    # 7. llm 응답 생성
    response = generate_response(user_input, results)

    return {
        "status": "success",
        "user_response": response,
        "total_job_info_list": job_info_list,
        "retrieved_job_info_list": results,
    }

    
    




