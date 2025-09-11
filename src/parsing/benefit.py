def parse_benefit_text(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')

    return : str : 복리후생 정보 (읽기 편하게 포맷팅)
    """
    benefit_div = soup.find("div", class_="jv_cont jv_benefit")
    if not benefit_div:
        return ""

    lines = []

    # 제목
    title_tag = benefit_div.find("h2", class_="jv_title")
    title = title_tag.get_text(strip=True) if title_tag else "복리후생 정보"
    lines.append(title)
    lines.append("-" * len(title))  # 제목 아래 구분선

    # dt-dd 쌍
    dts = benefit_div.find_all("dt")
    dds = benefit_div.find_all("dd")
    for dt, dd in zip(dts, dds):
        key = dt.get_text(strip=True)
        value = dd.get_text(strip=True)
        lines.append(f"{key}: {value}")

    return "\n".join(lines)
