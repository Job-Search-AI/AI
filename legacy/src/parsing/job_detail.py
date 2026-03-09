def parse_job_detail_text(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')

    return : str : 상세내용
    """
    detail_div = soup.find("div", class_="detail")
    if not detail_div:
        return ""
    lines = []
    
    lines.append("-" * 10)  
    lines.append("상세내용:")

    # 줄바꿈 살려서 텍스트 추출
    detail_content = detail_div.get_text(separator="\n", strip=True)
    
    lines.append(detail_content)
    lines.append("-" * 10)  
    
    return "\n".join(lines)