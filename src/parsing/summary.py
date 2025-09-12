def parse_summary_text(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')

    return : str : 요약 정보 (읽기 편하게 포맷팅)
    """
    summary_div = soup.find("div", class_="jv_cont jv_summary")

    if not summary_div:
        return ""

    lines = []
    lines.append("-" * 10)  
    lines.append("요약 정보:")

    # col 안의 dt-dd 쌍 가져오기
    for col in summary_div.find_all("div", class_="col"):
        for dl in col.find_all("dl"):
            key = dl.dt.get_text(strip=True)
            value = dl.dd.get_text(strip=True)
            lines.append(f"{key}: {value}")

        lines.append("")  # 컬럼 구분을 위해 빈 줄 추가
        
    lines.append("-" * 10)  

    return "\n".join(lines)