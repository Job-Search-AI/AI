from src import extract_job_major_info, print_job_summary, crawl_job_html_from_saramin, similarity_docs_retrieval, generate_response, get_device, print_device_info
# device 설정

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

# device 정보 출력
print("=== Job Search AI 시스템 시작 ===")
device = get_device('auto')
print_device_info(device)

print(f"사용 가능한 함수들:")
print(f"- extract_job_major_info: {extract_job_major_info}")
print(f"- print_job_summary: {print_job_summary}")
print(f"- crawl_job_html_from_saramin: {crawl_job_html_from_saramin}")
print(f"- similarity_docs_retrieval: {similarity_docs_retrieval}")
print(f"- generate_response: {generate_response}")
