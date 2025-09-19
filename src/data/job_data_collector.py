"""
채용공고 크롤링 데이터를 메타데이터로 변환하고 JSONL 파일로 저장하는 모듈
data_collector.py와 유사한 방식으로 동작
"""

import sys
import os
import json
from typing import List, Dict, Any

sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")

from src.crawling.job_crawler import crawl_job_html_from_saramin
from src.parsing.metadata_converter import convert_html_list_to_metadata_list


def save_job_metadata_to_jsonl(url: str, file_path: str, max_count: int = 50):
    """
    채용공고를 크롤링하고 메타데이터로 변환하여 JSONL 파일로 저장
    
    Args:
        url: 사람인 채용 정보 검색 URL
        file_path: 저장할 JSONL 파일 경로
        max_count: 최대 크롤링할 채용공고 수
    """
    print(f"채용공고 메타데이터 수집 시작")
    print(f"URL: {url}")
    print(f"저장 경로: {file_path}")
    print(f"최대 수집 수: {max_count}개")
    
    try:
        # 사람인 채용 정보 HTML 크롤링
        print("HTML 크롤링...")
        html_contents = crawl_job_html_from_saramin(url, max_count)
        
        if not html_contents:
            print("크롤링된 HTML이 없습니다.")
            return
        
        print(f"크롤링 완료: {len(html_contents)}개 HTML 수집")
        
        # HTML을 메타데이터로 변환
        print("메타데이터 변환...")
        metadata_list = convert_html_list_to_metadata_list(html_contents, url)
        
        if not metadata_list:
            print("변환된 메타데이터가 없습니다.")
            return
        
        print(f"메타데이터 변환 완료: {len(metadata_list)}개")
        
        # 시작 ID 결정
        start_id = 1
        if os.path.exists(file_path):
            # 기존 파일이 있으면 마지막 ID 확인
            with open(file_path, "r", encoding="utf-8") as f:
                last_line = None
                for line in f:
                    last_line = line.strip()
                if last_line:
                    try:
                        last_json = json.loads(last_line)
                        start_id = last_json.get("id", 0) + 1
                    except json.JSONDecodeError:
                        print("기존 파일의 마지막 줄 파싱 실패, ID 1부터 시작")
        
        print(f"JSONL 파일 저장 (시작 ID: {start_id})")
        
        # JSONL 파일로 저장
        saved_count = 0
        with open(file_path, "a", encoding="utf-8") as f:
            for idx, metadata in enumerate(metadata_list, start=start_id):
                # 메타데이터 품질 검사
                if not is_valid_metadata(metadata):
                    print(f"ID {idx}: 품질 기준 미달로 제외")
                    continue
                
                # JSON 객체 생성
                json_obj = {
                    "id": idx,
                    "data": metadata
                }
                
                # JSONL 형식으로 저장
                f.write(json.dumps(json_obj, ensure_ascii=False) + "\n")
                saved_count += 1
                
                print(f"ID {idx}: {metadata['title'][:50]}... 저장")
        
        print(f"전체 크롤링: {len(html_contents)}개")

    except Exception as e:
        print(f"데이터 수집 중 오류 발생: {e}")


def is_valid_metadata(metadata: Dict[str, Any]) -> bool:
    """
    메타데이터의 품질을 검사하여 저장할 가치가 있는지 판단
    
    Args:
        metadata: 검사할 메타데이터
    
    Returns:
        bool: 유효하면 True, 그렇지 않으면 False
    """
    # 필수 필드 존재 및 유효성 검사
    required_fields = ['title', 'company', 'description']
    
    for field in required_fields:
        value = metadata.get(field, "")
        if not value or value in [""]:
            return False
    
    return True


def load_job_metadata_from_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """
    JSONL 파일에서 메타데이터 로드
    
    Args:
        file_path: JSONL 파일 경로
    
    Returns:
        List[Dict]: 메타데이터 리스트
    """
    metadata_list = []
    
    if not os.path.exists(file_path):
        print(f"파일이 존재하지 않습니다: {file_path}")
        return metadata_list
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                json_obj = json.loads(line)
                metadata = json_obj.get("data", {})
                metadata_list.append(metadata)
    
    return metadata_list



if __name__ == "__main__":
    # 테스트 실행
    test_url = "https://www.saramin.co.kr/zf_user/search?loc_mcd=101000&cat_kewd=108%2C109&company_cd=0%2C1%2C2%2C3%2C4%2C5%2C6%2C7%2C9%2C10&exp_cd=1&edu_min=6&edu_max=11&edu_none=y&panel_type=&search_optional_item=y&search_done=y&panel_count=y&preview=y"
    
    # 데이터 저장 경로
    data_path = "/content/drive/MyDrive/ai_enginner/job_search/AI/data/job_metadata.jsonl"
    
    # 디렉토리 생성
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    
    # 메타데이터 수집 및 저장 (테스트용으로 3개만)
    save_job_metadata_to_jsonl(test_url, data_path, max_count=3)
    
    # 저장된 데이터 로드 및 통계
    print("저장된 데이터 확인")
    loaded_data = load_job_metadata_from_jsonl(data_path)
    print(f"메타데이터 로드 완료: {len(loaded_data)}개")