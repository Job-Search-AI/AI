def parse_benefit_text(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')

    return : str : 복리후생 정보 (읽기 편하게 포맷팅)
    """
    benefit_div = soup.find("div", class_="jv_cont jv_benefit")
    if not benefit_div:
        return ""

    lines = []
    lines.append("-" * 10)  
    lines.append("복리후생:")

    # dt-dd 쌍
    dts = benefit_div.find_all("dt")
    dds = benefit_div.find_all("dd")
    for dt, dd in zip(dts, dds):
        key = dt.get_text(strip=True)
        value = dd.get_text(strip=True)
        lines.append(f"{key}: {value}")
    
    lines.append("-" * 10)

    return "\n".join(lines)
