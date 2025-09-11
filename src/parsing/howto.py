def parse_howto(soup):
    how_to_el = soup.select_one("div.jv_cont.jv_howto")
    if not how_to_el:
        return {}
    title = how_to_el.select_one("h2.jv_title").get_text(strip=True)

    data = {}

    # 남은 기간
    timer = how_to_el.select_one(".info_timer")
    if timer:
        data["남은 기간"] = timer.get_text(strip=True)

    # 시작일 / 마감일
    for dl in how_to_el.select(".info_period"):
        dts = dl.select("dt")
        dds = dl.select("dd")
        for dt, dd in zip(dts, dds):
            data[dt.get_text(strip=True)] = dd.get_text(strip=True)

    # 지원방법, 접수양식
    for dl in how_to_el.select(".guide"):
        dts = dl.select("dt")
        dds = dl.select("dd")
        for dt, dd in zip(dts, dds):
            # 지원방법은 링크도 함께 저장
            if dd.select_one("a"):
                data[dt.get_text(strip=True)] = {
                    "text": dd.get_text(strip=True),
                    "url": dd.select_one("a")["href"]
                }
            else:
                data[dt.get_text(strip=True)] = dd.get_text(strip=True)

    return {title: data}