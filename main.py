print("=== Job Search AI 시스템 시작 ===")
# pip install -q selenium ipywidgets bitsandbytes

import sys
import os

os.system("pip install -q selenium ipywidgets bitsandbytes")

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
html_content = crawl_job_html_from_saramin(generated_url, USER_INFO, 3)

# 3) 채용 정보 파싱
documents = parsing_job_info(html_content)

# 4) 임베딩 리트리버
retrieved_documents, retrieved_scores = similarity_docs_retrieval(final_query, documents)

# 5) LLM 사용자 질문 응답
response = generate_response(final_query, retrieved_documents)

html_content = crawl_job_html_from_saramin(generated_url, USER_INFO, 3)

# 3) 채용 정보 파싱
documents = parsing_job_info(html_content)

# 4) 임베딩 리트리버
retrieved_documents, retrieved_scores = similarity_docs_retrieval(final_query, documents)

# 5) LLM 사용자 질문 응답
response = generate_response(final_query, retrieved_documents)
