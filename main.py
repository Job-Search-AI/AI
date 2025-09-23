print("=== Job Search AI 시스템 시작 ===")
# pip install -q selenium bitsandbytes

import sys
import os

os.system("pip install -q selenium bitsandbytes")

from src import (
    crawl_job_html_from_saramin,
    similarity_docs_retrieval,
    generate_response,
    parsing_job_info,
)
from src.url_exchaging.interactive_query import interactive_query_handler
from config import USER_INFO

# 1) 사용자와 대화형으로 URL 생성
generated_url, final_query = interactive_query_handler()

# 2) 사람인 채용 정보 html 추출
html_contents = crawl_job_html_from_saramin(search_url, max_jobs)

# 3) 채용 정보 메타데이터 추출
metadata_list = convert_html_list_to_metadata_list(html_contents, search_url)

# 4. 메타데이터로 검색 인덱스 구축
search_documents = create_search_documents_from_metadata(valid_metadata)
retriever.build_index(search_documents)

# 4) 임베딩 리트리버
retrieved_docs, scores = retriever.search(user_query, top_k=5)

# 5. 검색 결과로 LLM 요약 생성
card_metadata_list = batch_process_jobs(user_query, search_results_metadata)

