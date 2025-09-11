def parse_job_detail(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')
    """
    detail_div = soup.find("div", class_="detail")
    if not detail_div:
        return {}

    # 줄바꿈 살려서 텍스트 추출
    detail_content = detail_div.get_text(separator="\n", strip=True)
    
    return {"상세내용": detail_content}