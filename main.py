print("=== Job Search AI 시스템 시작 ===")
# pip install -q selenium ipywidgets bitsandbytes

import sys
import os

os.system("pip install -q selenium ipywidgets bitsandbytes")

# 가장 먼저 HF_HOME을 설정해야 모델, 토크나이저를 원하는 캐쉬 디렉토리에서 불러올수있다.
cache_dir = '/content/drive/MyDrive/ai_enginner/job_search/AI/cache/'
project_dir = '/content/drive/MyDrive/ai_enginner/job_search/AI/'
sys.path.append(project_dir)
os.environ['HF_HOME'] = cache_dir

from src import (
    extract_job_major_info,
    print_job_summary,
    crawl_job_html_from_saramin,
    similarity_docs_retrieval,
    generate_response
)

print("모든 함수들이 성공적으로 import되었습니다!")

# 더미 데이터 생성
user_info = {
        "cat_kewd": "84", # 직무 코드
        "keydownAccess": "", # 검색 키워드
        "loc_mcd": "101000", # 지역 코드
        "exp_cd": "1", # 경력 코드
        "exp_none": "y", # 경력 무관
        "edu_none": "y", # 학력 무관
        "edu_min": "6", # 학력 최소
        "edu_max": "9", # 학력 최대
        "search_done": "y", # 검색 완료
    }

# 사람인 채용 정보 html 추출
html_content = crawl_job_html_from_saramin(user_info)

# #content > div.recruit_list_renew > div 영역 내의 채용 정보 추출
job_data = extract_job_major_info(html_content)

# 채용 정보 요약 출력
print_job_summary(job_data)

# 사용자 질문
user_query = "파이썬 장고를 개발자 채용공고만 알려줘"

# 임베딩 리트리버
doc_score_pairs = similarity_docs_retrieval(user_query, job_data)

# LLM 사용자 질문 응답
response = generate_response(user_query, job_data)
print(f"LLM 응답: {response}")

