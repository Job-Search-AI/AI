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

    # 사용자 입력 NER 인식
    entity = predict_crf_bert(user_input, _MODEL_CACHE["bert_model"], _MODEL_CACHE["crf"], _MODEL_CACHE["tokenizer"], _MODEL_CACHE['device'])

    # 사용자 입력 엔티티 표준화
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
        
    # 누락된 정보가 없다면, 정상 진행
    return {
        "status": status,
        "message": message,
        "missing_fields": missing_fields,
        "normalized_entities": normalized_entities
    }

