def parse_location(soup):
    location = soup.select_one("div.location").get_text(strip=True)
    
    return { "근무지 위치" : location}