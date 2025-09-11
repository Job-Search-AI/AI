def parse_summary(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')
    """
    summary_div = soup.find("div", class_="jv_cont jv_summary")

    if not summary_div:
        return {}

    result = {}

    # jv_title을 키로 사용
    title = summary_div.find("h2", class_="jv_title").get_text(strip=True)

    # col 안의 dt-dd 쌍 가져오기
    for col in summary_div.find_all("div", class_="col"):
        for dl in col.find_all("dl"):
            key = dl.dt.get_text(strip=True)
            value = dl.dd.get_text(strip=True)
            result[key] = value

    return {title: result}