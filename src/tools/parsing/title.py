def parse_title_text(soup):
    """
    soup : BeautifulSoup
    """

    title_el = soup.find("h1", class_="tit_job")

    if not title_el:
        return ""
    
    title = title_el.get_text(strip=True)

    lines = []
    lines.append("-" * 10)
    lines.append("공고제목: ")
    lines.append(title)
    lines.append("-" * 10)

    return "\n".join(lines)
