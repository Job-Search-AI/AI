print("=== Job Search AI 시스템 시작 ===")
# pip install -q selenium bitsandbytes

# os.system("pip install -q selenium bitsandbytes")

from src import (
    crawl_job_html_from_saramin,
    similarity_docs_retrieval,
    generate_response,
    parsing_job_info,
    predict_crf_bert,
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

# 사용자 입력 검증

# 2) NER 인식
entity = predict_crf_bert('야, ERP 컨설턴트 경력 5년 대졸이면, 경기 공고 좋은 거 없냐?', _MODEL_CACHE["bert_model"], _MODEL_CACHE["crf"], _MODEL_CACHE["tokenizer"], _MODEL_CACHE["device"])

# 3) URL 생성

# 4) 사람인 채용 정보 html 추출
html_contents = crawl_job_html_from_saramin(generated_url, max_jobs)

# 5) 채용 정보 메타데이터 추출
metadata_list = convert_html_list_to_metadata_list(html_contents, search_url)

# 6) 메타데이터로 검색 인덱스 구축
search_documents = create_search_documents_from_metadata(metadata_list)
retriever.build_index(search_documents)

# 7) 임베딩 리트리버
retrieved_docs, scores = retriever.search(user_query, top_k=5)

# 8) 검색 결과로 LLM 요약 생성
card_metadata_list = batch_process_jobs(user_query, search_results_metadata)

