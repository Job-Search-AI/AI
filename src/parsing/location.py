def parse_location_text(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')

    return : str : 근무지 위치
    """
    if not soup.select_one("div.location"):
        return ""
    
    location = soup.select_one("div.location").get_text(strip=True)
    
    return "근무지 위치 : " + location  