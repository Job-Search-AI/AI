from bs4 import BeautifulSoup

from src.parsing.summary import parse_summary_text
from src.parsing.company_info import parse_company_info_text
from src.parsing.job_detail import parse_job_detail_text
from src.parsing.benefit import parse_benefit_text
from src.parsing.location import parse_location_text
from src.parsing.howto import parse_howto_text
from src.parsing.applicant_stats import parse_applicant_stats_text

from src.crawling.job_crawler import crawl_job_html_from_saramin
from config import USER_INFO

def parsing_job_info(html_contents):
    """
    html_contents : list[str]

    return : list[str]  
    """
    job_info_list = []

    for html_content in html_contents:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 각 파트 결과를 리스트에 담기
        parts = [
            parse_company_info_text(soup),
            parse_summary_text(soup),
            parse_benefit_text(soup),
            parse_location_text(soup),
            parse_howto_text(soup),
            parse_applicant_stats_text(soup)
        ]

        # 빈 줄 2개 정도로 구분하여 합치기
        parsed_text = "\n\n".join(parts)
        job_info_list.append(parsed_text)

    return job_info_list


if __name__ == "__main__":
    html_contents = crawl_job_html_from_saramin(USER_INFO, 3)
    job_info = parsing_job_info(html_contents)
    print(job_info)