def parse_location_text(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')

    return : str : 근무지 위치
    """
    location_div = soup.find("div", class_="jv_location")
    if not location_div:
        return ""
    
    lines = []
    lines.append("-" * 10)
    lines.append("근무지 위치:")
    
    location = location_div.get_text(strip=True)
    
    lines.append(location)
    lines.append("-" * 10)
    
    return "\n".join(lines)  