import concurrent.futures
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

TITLE_FILTER_WORDS = [
    "교육생 모집",
    "교육생",
    "수강생 모집",
    "수강생",
    "연수생 모집",
    "연수생",
    "훈련생 모집",
    "훈련생",
    "참여자 모집",
    "국비지원",
    "국비무료",
    "전액국비",
    "국비",
    "kdt",
    "취업과정",
    "교육과정",
    "양성과정",
    "훈련과정",
    "부트캠프",
    "내일배움",
    "아카데미",
]


def crawl_job_html_from_saramin(url, max_count=None):
    """
    url: 사용자 조건을 적용한 url
    max_count: 크롤링 데이터 개수
    """
    if max_count is not None:
        if isinstance(max_count, int):
            if max_count <= 0:
                return []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        )
    }

    try:
        list_response = requests.get(url, headers=headers, timeout=20)
        list_response.raise_for_status()
    except Exception as e:
        print(f"목록 페이지 요청 실패: {e}")
        return []

    list_soup = BeautifulSoup(list_response.text, "lxml")

    parsed_list = urlparse(url)
    base_url = "https://www.saramin.co.kr"
    if parsed_list.scheme and parsed_list.netloc:
        base_url = f"{parsed_list.scheme}://{parsed_list.netloc}"

    links = list_soup.select("div.item_recruit div.area_job h2 a[href]")
    rec_items = []
    seen = set()
    count = 0

    for link in links:
        href = link.get("href")
        if not href:
            continue

        list_title_text = link.get_text(" ", strip=True)
        blocked = False
        blocked_word = ""
        title_for_filter = list_title_text.lower().replace(" ", "")
        for word in TITLE_FILTER_WORDS:
            word_for_filter = word.lower().replace(" ", "")
            if word_for_filter in title_for_filter:
                blocked = True
                blocked_word = word
                break

        if blocked:
            print("목록 제목 키워드 필터로 스킵:")
            print(f"  목록 제목: {list_title_text}")
            print(f"  매칭 키워드: {blocked_word}")
            continue

        full_href = urljoin(base_url, href)
        parsed_href = urlparse(full_href)
        query_map = parse_qs(parsed_href.query)

        rec_values = query_map.get("rec_idx")
        if not rec_values:
            continue

        rec_idx = rec_values[0].strip()
        if not rec_idx:
            continue

        if rec_idx in seen:
            continue

        seen.add(rec_idx)
        rec_items.append(
            {
                "idx": count,
                "rec_idx": rec_idx,
                "referer": full_href,
                "list_title": list_title_text,
            }
        )
        count += 1

        if max_count is not None:
            if isinstance(max_count, int):
                if count >= max_count:
                    break

    if len(rec_items) == 0:
        return []

    post_url = urljoin(base_url, "/zf_user/jobs/relay/view-ajax")

    def fetch_one(item):
        idx = item["idx"]
        rec_idx = item["rec_idx"]
        referer = item["referer"]
        list_title = item["list_title"]

        request_headers = dict(headers)
        request_headers["Referer"] = referer

        try:
            ajax_response = requests.post(
                post_url,
                data={"rec_idx": rec_idx},
                headers=request_headers,
                timeout=20,
            )
            ajax_response.raise_for_status()
        except Exception as e:
            print(f"상세 view-ajax 요청 실패(rec_idx={rec_idx}): {e}")
            return idx, None

        detail_soup = BeautifulSoup(ajax_response.text, "lxml")
        wrap = detail_soup.select_one("div.wrap_jv_cont")
        if wrap is None:
            wrap = detail_soup

        title_html = ""
        detail_title_text = ""
        title_node = wrap.select_one("h1.tit_job")
        if title_node is not None:
            title_html = str(title_node)
            detail_title_text = title_node.get_text(" ", strip=True)

        blocked = False
        blocked_word = ""
        title_for_filter = detail_title_text.lower().replace(" ", "")
        for word in TITLE_FILTER_WORDS:
            word_for_filter = word.lower().replace(" ", "")
            if word_for_filter in title_for_filter:
                blocked = True
                blocked_word = word
                break

        if blocked:
            print("상세 제목 키워드 필터로 스킵:")
            print(f"  목록 제목: {list_title}")
            print(f"  상세 제목: {detail_title_text}")
            print(f"  매칭 키워드: {blocked_word}")
            return idx, None

        summary_html = ""
        summary_node = wrap.select_one("div.jv_cont.jv_summary")
        if summary_node is not None:
            summary_html = str(summary_node)

        detail_text = ""
        detail_node = wrap.select_one("div.jv_cont.jv_detail")
        if detail_node is not None:
            iframe_node = detail_node.select_one("iframe[src]")
            if iframe_node is not None:
                iframe_src = iframe_node.get("src")
                if iframe_src:
                    iframe_url = urljoin(base_url, iframe_src)
                    try:
                        iframe_response = requests.get(
                            iframe_url,
                            headers=request_headers,
                            timeout=20,
                        )
                        iframe_response.raise_for_status()
                        iframe_soup = BeautifulSoup(iframe_response.text, "lxml")
                        if iframe_soup.body is not None:
                            detail_text = iframe_soup.body.get_text("\n", strip=True)
                        else:
                            detail_text = iframe_soup.get_text("\n", strip=True)
                    except Exception as e:
                        print(f"iframe 본문 요청 실패(rec_idx={rec_idx}): {e}")
                        detail_text = detail_node.get_text("\n", strip=True)
                else:
                    detail_text = detail_node.get_text("\n", strip=True)
            else:
                detail_text = detail_node.get_text("\n", strip=True)

        how_html = ""
        how_node = wrap.select_one("div.jv_cont.jv_howto")
        if how_node is not None:
            how_html = str(how_node)

        company_html = ""
        company_node = wrap.select_one("div.jv_cont.jv_company")
        if company_node is not None:
            company_html = str(company_node)

        benefit_html = ""
        benefit_node = wrap.select_one("div.jv_cont.jv_benefit")
        if benefit_node is not None:
            benefit_html = str(benefit_node)

        location_text = ""
        location_node = wrap.select_one("div.jv_cont.jv_location")
        if location_node is not None:
            location_text = location_node.get_text(" ", strip=True)

        statics_html = ""
        statics_node = wrap.select_one("div.jv_cont.jv_statics")
        if statics_node is not None:
            statics_html = str(statics_node)

        combined_html = "".join(
            [
                title_html,
                "\n",
                summary_html,
                "\n",
                f'<div class="detail">{detail_text}</div>',
                "\n",
                how_html,
                "\n",
                company_html,
                "\n",
                benefit_html,
                "\n",
                f'<div class="location">{location_text}</div>',
                "\n",
                statics_html,
            ]
        )

        if not combined_html.strip():
            return idx, None

        return idx, combined_html

    raw_results = [None] * len(rec_items)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        future_map = {}
        for item in rec_items:
            future = pool.submit(fetch_one, item)
            future_map[future] = item["idx"]

        for future in concurrent.futures.as_completed(future_map):
            mapped_idx = future_map[future]
            try:
                result_idx, html = future.result()
                if html is not None:
                    raw_results[result_idx] = html
            except Exception as e:
                print(f"상세 처리 실패(idx={mapped_idx}): {e}")

    html_results = []
    for html in raw_results:
        if html:
            html_results.append(html)

    return html_results
