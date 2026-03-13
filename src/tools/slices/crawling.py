from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def crawl_job_html_from_saramin(url, max_count=None):
    """
    url: 사용자 조건을 적용한 url
    max_count: 크롤링 데이터 개수
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    }

    details_html_parts = []
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    target_elements = soup.select(".item_recruit")

    detail_items = []
    for element in target_elements:
        link_el = element.select_one("div.area_job h2 a")
        if link_el is None:
            continue

        href = link_el.get("href")
        if not href:
            continue

        if href.startswith("/"):
            href = urljoin("https://www.saramin.co.kr", href)

        list_title = ""
        span_el = element.select_one("h2.job_tit > a > span")
        if span_el is not None:
            list_title = span_el.get_text(" ", strip=True)

        detail_items.append({"href": href, "list_title": list_title})

    index = 0
    for item in detail_items:
        if max_count is not None and index >= max_count:
            break

        detail_url = item.get("href")
        if not detail_url:
            continue

        index += 1
        detail_res = requests.get(detail_url, headers=headers, timeout=20)
        if detail_res.status_code >= 400:
            continue

        detail_soup = BeautifulSoup(detail_res.text, "lxml")
        first_section = detail_soup.select_one(".wrap_jview > section:first-of-type > div.wrap_jv_cont")
        if first_section is None:
            continue

        title_el = first_section.select_one("h1.tit_job")
        summary_el = first_section.select_one("div.jv_cont.jv_summary")
        detail_el = first_section.select_one("div.jv_cont.jv_detail")
        how_el = first_section.select_one("div.jv_cont.jv_howto")
        corp_el = first_section.select_one("div.jv_cont.jv_company")
        benefit_el = first_section.select_one("div.jv_cont.jv_benefit")
        location_el = first_section.select_one("div.jv_cont.jv_location")
        applicant_el = first_section.select_one("div.jv_cont.jv_statics")

        detail_inner_text = ""
        if detail_el is not None:
            detail_inner_text = detail_el.get_text("\n", strip=True)

        combined_html = ""
        if title_el is not None:
            combined_html += str(title_el)
        if summary_el is not None:
            combined_html += "\n" + str(summary_el)
        if detail_inner_text:
            combined_html += f"\n<div class=\"detail\">{detail_inner_text}</div>"
        if how_el is not None:
            combined_html += "\n" + str(how_el)
        if corp_el is not None:
            combined_html += "\n" + str(corp_el)
        if benefit_el is not None:
            combined_html += "\n" + str(benefit_el)
        if location_el is not None:
            combined_html += "\n" + str(location_el)
        if applicant_el is not None:
            combined_html += "\n" + str(applicant_el)

        if combined_html:
            details_html_parts.append(combined_html)

    return details_html_parts
