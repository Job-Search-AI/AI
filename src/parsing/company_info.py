def parse_company_info(soup):
    company_section = soup.select_one("div.jv_cont.jv_company")
    title = company_section.select_one("h2.jv_title_heading").get_text(strip=True)

    data = {}

    # 회사명
    company_name = company_section.select_one(".basic_info h3")
    if company_name:
        data["회사명"] = company_name.get_text(strip=True)

    # 로고
    logo = company_section.select_one(".logo img")
    if logo and logo.get("src"):
        data["로고"] = logo["src"]

    # dl -> dt:dd
    for dl in company_section.select(".info_area dl"):
        dt = dl.select_one("dt").get_text(strip=True)
        dd = dl.select_one("dd").get_text(strip=True)
        data[dt] = dd

    return {title: data}
