import sys
import os
import json

sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")

from src.crawling import crawl_job_html_from_saramin
from src.parsing import parsing_job_info

def save_data_to_jsonl(url, file_path):
    """
    url : str - 사람인 채용 정보 url
    file_path : str - JSONL 파일 경로
    """
    # 사람인 채용 정보 html 추출
    html_content = crawl_job_html_from_saramin(url, 50)
    parsed_job_info = parsing_job_info(html_content)

    # 시작 id를 1로 초기화
    start_id = 1
    
    # 파일이 이미 존재하는지 확인
    if os.path.exists(file_path):
        # 존재하면 마지막 줄을 읽어 마지막 id를 확인
        with open(file_path, "r", encoding="utf-8") as f:
            last_line = None
            for line in f:
                last_line = line.strip()  # 마지막 줄만 기억
            if last_line:  # 파일에 내용이 있으면
                last_json = json.loads(last_line)  # JSON 문자열을 dict로 변환
                start_id = last_json.get("id", 0) + 1  # 마지막 id + 1부터 시작
    
    # JSONL 파일을 이어쓰기 모드로 연다
    with open(file_path, "a", encoding="utf-8") as f:
        # 데이터 리스트를 순회
        for idx, item in enumerate(parsed_job_info, start=start_id):
            # 하나의 데이터 항목을 딕셔너리 형태로 만든다
            json_obj = {
                "id": idx,     # 순번을 id로 저장
                "data": item   # 실제 문장 데이터를 data로 저장
            }
            # json.dumps로 딕셔너리를 JSON 문자열로 변환하고, f.write로 파일에 기록
            f.write(json.dumps(json_obj, ensure_ascii=False) + "\n")  # 한 줄씩 기록

    print("사람인 채용 정보 추출 시작...")

if __name__ == "__main__":
    # 서울/신입/딥러닝,머신러닝/고교~4년제
    url = "https://www.saramin.co.kr/zf_user/search?loc_mcd=101000&cat_kewd=108%2C109&company_cd=0%2C1%2C2%2C3%2C4%2C5%2C6%2C7%2C9%2C10&exp_cd=1&edu_min=6&edu_max=11&edu_none=y&panel_type=&search_optional_item=y&search_done=y&panel_count=y&preview=y"

    data_path = "/content/drive/MyDrive/ai_enginner/job_search/AI/data/eval/retrieval/data.jsonl"

    save_data_to_jsonl(url, data_path)