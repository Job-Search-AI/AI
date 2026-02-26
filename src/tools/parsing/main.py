from bs4 import BeautifulSoup

# parsing.main도 tools 내부 모듈만 사용하도록 경로를 통일한다.
from src.tools.parsing.summary import parse_summary_text
from src.tools.parsing.company_info import parse_company_info_text
from src.tools.parsing.job_detail import parse_job_detail_text
from src.tools.parsing.benefit import parse_benefit_text
from src.tools.parsing.location import parse_location_text
from src.tools.parsing.howto import parse_howto_text
from src.tools.parsing.applicant_stats import parse_applicant_stats_text
from src.tools.parsing.title import parse_title_text
from src.tools.parsing.metadata_converter import convert_html_list_to_metadata_list

from src.tools.slices.crawling import crawl_job_html_from_saramin
from config import EVAL_URL

def parsing_job_info(html_contents):
    """
    html 파싱

    html_contents : list[str]

    return : list[str]  
    """
    job_info_list = []

    for html_content in html_contents:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 각 파트 결과를 리스트에 담기
        parts = [
            "*" * 10,
            parse_title_text(soup),
            parse_summary_text(soup),
            parse_benefit_text(soup),
            parse_location_text(soup),
            parse_job_detail_text(soup),
            parse_howto_text(soup),
            parse_applicant_stats_text(soup),
            parse_company_info_text(soup),
            "*" * 10,
        ]

        # 빈 줄 2개 정도로 구분하여 합치기
        parsed_text = "\n\n".join(parts)
        job_info_list.append(parsed_text)

    return job_info_list


def parsing_job_metadata(html_contents, base_url=""):
    """
    html_contents를 메타데이터 형식으로 파싱
    
    Args:
        html_contents: list[str] - HTML 컨텐츠 리스트
        base_url: str - 기본 URL
    
    Returns:
        list[dict] - 메타데이터 딕셔너리 리스트
    """
    # HTML을 직접 메타데이터로 변환
    metadata_list = convert_html_list_to_metadata_list(html_contents, base_url)
    
    return metadata_list


if __name__ == "__main__":
    url = 'https://www.saramin.co.kr/zf_user/search?searchType=search?loc_mcd=101000&cat_kewd=109&exp_min=2&exp_max=2&edu_min=8&edu_max=11&edu_none=y&exp_none=y'
    html_contents = crawl_job_html_from_saramin(url, 3)
    job_info = parsing_job_info(html_contents)
    print("=== 텍스트 파싱 결과 ===")
    print(job_info)
    
    print("\n=== 메타데이터 파싱 결과 ===")
    metadata = parsing_job_metadata(html_contents, url)
    for i, meta in enumerate(metadata):
        print(f"\n--- 채용공고 {i+1} ---")
        for key, value in meta.items():
            print(f"{key}: {value}")
