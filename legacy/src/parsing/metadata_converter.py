"""
채용공고 HTML을 메타데이터 형식으로 직접 변환하는 모듈
기존 파싱 함수들을 활용하여 구조화된 데이터 생성
"""

import sys
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup

sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")


def extract_title_from_soup(soup: BeautifulSoup) -> str:
    """BeautifulSoup에서 제목 추출"""
    title_el = soup.find("h1", class_="tit_job")
    if title_el:
        return title_el.get_text(strip=True)
    return "제목 정보 없음"


def extract_company_from_soup(soup: BeautifulSoup) -> str:
    """BeautifulSoup에서 회사명 추출"""
    # 회사정보 섹션에서 회사명 추출
    company_section = soup.select_one("div.jv_cont.jv_company")
    if company_section:
        company_name_tag = company_section.select_one(".basic_info h3")
        if company_name_tag:
            company_name = company_name_tag.get_text(strip=True)
            # 불필요한 텍스트 제거
            if "관심기업" in company_name:
                company_name = company_name.replace("관심기업", "").strip()
            return company_name
    return "회사명 정보 없음"


def extract_summary_fields_from_soup(soup: BeautifulSoup) -> Dict[str, str]:
    """BeautifulSoup에서 요약 정보 추출 (경력, 학력, 급여, 근무지역 등)"""
    summary_data = {
        "experience": "정보 없음",
        "education": "정보 없음", 
        "salary": "정보 없음",
        "location": "정보 없음",
        "employment_type": "정보 없음"
    }
    
    summary_div = soup.find("div", class_="jv_cont jv_summary")
    if not summary_div:
        return summary_data
    
    # col 안의 dt-dd 쌍 가져오기
    for col in summary_div.find_all("div", class_="col"):
        for dl in col.find_all("dl"):
            dt = dl.find("dt")
            dd = dl.find("dd") 
            
            if not dt or not dd:
                continue
                
            key = dt.get_text(strip=True)
            value = dd.get_text(strip=True)
            
            # 키워드별로 매핑
            if "경력" in key:
                summary_data["experience"] = value
            elif "학력" in key:
                summary_data["education"] = value
            elif "급여" in key or "연봉" in key:
                summary_data["salary"] = value
            elif "근무지역" in key or "지역" in key:
                summary_data["location"] = value
            elif "근무형태" in key:
                summary_data["employment_type"] = value
    
    return summary_data


def extract_job_description_from_soup(soup: BeautifulSoup) -> str:
    """BeautifulSoup에서 채용 상세 내용 추출"""
    detail_div = soup.find("div", class_="detail")
    if detail_div:
        # 줄바꿈 살려서 텍스트 추출
        detail_content = detail_div.get_text(separator=" ", strip=True)
        return detail_content[:1000] + "..." if len(detail_content) > 1000 else detail_content
    return "상세 내용 정보 없음"


def convert_html_to_metadata(html_content: str, source_url: str = "") -> Dict[str, Any]:
    """
    HTML 컨텐츠를 메타데이터 딕셔너리로 변환
    
    Args:
        html_content: 사람인 채용공고 HTML 문자열
        source_url: 원본 URL
    
    Returns:
        Dict: 메타데이터 딕셔너리
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 각 필드 추출
        title = extract_title_from_soup(soup)
        company = extract_company_from_soup(soup)
        summary_fields = extract_summary_fields_from_soup(soup)
        description = extract_job_description_from_soup(soup)
        
        # 메타데이터 구성
        metadata = {
            "title": title,
            "company": company,
            "position": title,  # position은 title과 동일하게 처리
            "description": description,
            "experience": summary_fields["experience"],
            "education": summary_fields["education"],
            "location": summary_fields["location"],
            "salary": summary_fields["salary"],
            "employment_type": summary_fields["employment_type"],
            "url": source_url
        }
        
        return metadata
    
    except Exception as e:
        print(f"HTML 메타데이터 변환 중 오류 발생: {e}")
        # 오류 발생 시 기본 메타데이터 반환
        return {
            "title": "파싱 오류",
            "company": "정보 없음",
            "position": "정보 없음",
            "description": "파싱 중 오류가 발생했습니다.",
            "experience": "정보 없음",
            "education": "정보 없음",
            "location": "정보 없음",
            "salary": "정보 없음",
            "employment_type": "정보 없음",
            "url": source_url
        }


def convert_html_list_to_metadata_list(html_contents: List[str], base_url: str = "") -> List[Dict[str, Any]]:
    """
    HTML 컨텐츠 리스트를 메타데이터 리스트로 변환
    
    Args:
        html_contents: HTML 컨텐츠 리스트
        base_url: 기본 URL
    
    Returns:
        List[Dict]: 메타데이터 딕셔너리 리스트
    """
    metadata_list = []
    
    for i, html_content in enumerate(html_contents):
        # URL에 인덱스 추가하여 구분
        url = f"{base_url}#job_{i+1}" if base_url else f"job_{i+1}"
        metadata = convert_html_to_metadata(html_content, url)
        metadata_list.append(metadata)
    
    return metadata_list


if __name__ == "__main__":
    # 테스트용 샘플 HTML
    sample_html = """
    <h1 class="tit_job">AI 엔지니어 신입 채용</h1>
    <div class="jv_cont jv_summary">
        <div class="col">
            <dl><dt>경력</dt><dd>신입~3년</dd></dl>
            <dl><dt>학력</dt><dd>대학교 졸업</dd></dl>
        </div>
        <div class="col">
            <dl><dt>급여</dt><dd>3000~5000만원</dd></dl>
            <dl><dt>근무지역</dt><dd>서울특별시 강남구</dd></dl>
        </div>
    </div>
    <div class="jv_cont jv_company">
        <div class="basic_info">
            <h3>테크놀로지(주)관심기업</h3>
        </div>
    </div>
    <div class="detail">
        AI 모델 개발 및 최적화 업무를 담당할 신입 개발자를 채용합니다.
        Python, TensorFlow 경험 우대합니다.
    </div>
    """
    
    result = convert_html_to_metadata(sample_html, "https://example.com/job/1")
    
    print("=== 메타데이터 변환 결과 ===")
    for key, value in result.items():
        print(f"{key}: {value}")
