print("=== Job Search AI 시스템 시작 ===")
# pip install -q selenium ipywidgets bitsandbytes

import sys
import os

os.system("pip install -q selenium ipywidgets bitsandbytes")

# 가장 먼저 HF_HOME을 설정해야 모델, 토크나이저를 원하는 캐쉬 디렉토리에서 불러올수있다.
cache_dir = '/content/drive/MyDrive/ai_enginner/job_search/AI/cache/'
os.environ['HF_HOME'] = cache_dir

from src import (
    crawl_job_html_from_saramin,
    similarity_docs_retrieval,
    generate_response,
    parsing_job_info
)
from config import USER_INFO

print("모든 함수들이 성공적으로 import되었습니다!")

# 사람인 채용 정보 html 추출
html_content = crawl_job_html_from_saramin(USER_INFO, 3)

# #content > div.recruit_list_renew > div 영역 내의 채용 정보 추출
documents = parsing_job_info(html_content)

# 사용자 질문
query = "신입, 학력무관, 고졸이상 공고중에서 AI 엔지니어 공고들만 보여줘."

# 임베딩 리트리버
retrieved_documents, retrieved_scores = similarity_docs_retrieval(query, documents)

# LLM 사용자 질문 응답
response = generate_response(query, retrieved_documents)
print(f"LLM 응답: {response}")

