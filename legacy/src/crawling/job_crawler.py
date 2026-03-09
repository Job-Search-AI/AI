from .tools import crawl_job_html_from_saramin

if __name__ == "__main__":
    # python -m src.crawling.job_crawler
    print("사람인 채용 정보 추출 시작...")

    # 서울/신입/딥러닝,머신러닝/고교~4년제
    url = "https://www.saramin.co.kr/zf_user/search?loc_mcd=101000&cat_kewd=108%2C109&company_cd=0%2C1%2C2%2C3%2C4%2C5%2C6%2C7%2C9%2C10&exp_cd=1&edu_min=6&edu_max=11&edu_none=y&panel_type=&search_optional_item=y&search_done=y&panel_count=y&preview=y"

    # 사람인 채용 정보 html 추출
    html_content = crawl_job_html_from_saramin(url, 50)
    print(html_content)
