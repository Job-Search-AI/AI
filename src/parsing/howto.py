def parse_howto_text(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')

    return : str : 지원 방법 및 기간 정보 (읽기 편하게 포맷팅)
    """
    how_to_el = soup.select_one("div.jv_cont.jv_howto")
    if not how_to_el:
        return ""

    lines = []

    # 제목
    title_tag = how_to_el.select_one("h2.jv_title")
    title = title_tag.get_text(strip=True) if title_tag else "지원 방법 정보"
    lines.append(title)
    lines.append("-" * len(title))  # 제목 아래 구분선

    # 남은 기간
    timer = how_to_el.select_one(".info_timer")
    if timer:
        lines.append(f"남은 기간: {timer.get_text(strip=True)}")
        lines.append("")

    # 시작일 / 마감일
    for dl in how_to_el.select(".info_period"):
        dts = dl.select("dt")
        dds = dl.select("dd")
        for dt, dd in zip(dts, dds):
            lines.append(f"{dt.get_text(strip=True)}: {dd.get_text(strip=True)}")
        lines.append("")  # 컬럼 구분용 빈 줄

    # 지원방법, 접수양식
    for dl in how_to_el.select(".guide"):
        dts = dl.select("dt")
        dds = dl.select("dd")
        for dt, dd in zip(dts, dds):
            key = dt.get_text(strip=True)
            link = dd.select_one("a")
            if link:
                text = dd.get_text(strip=True)
                url = link["href"]
                lines.append(f"{key}: {text} (URL: {url})")
            else:
                lines.append(f"{key}: {dd.get_text(strip=True)}")
        lines.append("")

    return "\n".join(lines)
