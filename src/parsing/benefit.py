def parse_benefit(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')
    """
    benefit_div = soup.find("div", class_="jv_cont jv_benefit")
    if not benefit_div:
        return {}
        
    benefits = {}

    # jv_title을 키로 사용
    title = benefit_div.find("h2", class_="jv_title").get_text(strip=True)

    # 모든 dt-dd 쌍을 찾아서 딕셔너리에 추가
    for dt, dd in zip(benefit_div.find_all("dt"), benefit_div.find_all("dd")):
        key = dt.get_text(strip=True)
        value = dd.get_text(strip=True)
        benefits[key] = value

    return {title: benefits}