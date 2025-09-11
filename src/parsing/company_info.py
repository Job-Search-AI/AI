def parse_company_info_text(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')

    return : str : 회사 정보 (읽기 편하게 포맷팅)
    """
    company_section = soup.select_one("div.jv_cont.jv_company")
    if not company_section:
        return ""

    lines = []

    # 제목
    title_tag = company_section.select_one("h2.jv_title_heading")
    title = title_tag.get_text(strip=True) if title_tag else "회사 정보"
    lines.append(title)
    lines.append("-" * len(title))  # 제목 아래 구분선

    # 회사명
    company_name_tag = company_section.select_one(".basic_info h3")
    if company_name_tag:
        lines.append(f"회사명: {company_name_tag.get_text(strip=True)}")

    # dl -> dt: dd
    for dl in company_section.select(".info_area dl"):
        dt_tag = dl.select_one("dt")
        dd_tag = dl.select_one("dd")
        if dt_tag and dd_tag:
            key = dt_tag.get_text(strip=True)
            value = dd_tag.get_text(strip=True)
            lines.append(f"{key}: {value}")

    return "\n".join(lines)
