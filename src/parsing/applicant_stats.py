def parse_applicant_stats(soup):
    stats_section = soup.select_one("div.jv_cont.jv_statics")
    if not stats_section:
        return {}

    title = stats_section.select_one("h2.jv_title").get_text(strip=True)

    result = {}

    # 전체 지원자수
    total_dl = stats_section.select_one("dl.total")
    if total_dl:
        dt = total_dl.select_one("dt")
        dd = total_dl.select_one("dd span")
        if dt and dd:
            result[dt.get_text(strip=True)] = dd.get_text(strip=True)

    # box_chart 항목들
    charts = stats_section.select("div.box_chart")
    for chart in charts:
        chart_title = chart.select_one("strong.tit_stats")
        if not chart_title:
            continue
        chart_key = chart_title.get_text(strip=True)
        chart_data = {}

        # bar 형식
        for col in chart.select("div.col"):
            legend = col.select_one("em.legend")
            value = col.select_one("span.value")
            if legend and value:
                chart_data[legend.get_text(strip=True)] = value.get_text(strip=True)

        # 성별 현황 같은 donut 차트
        for dl in chart.select("dl"):
            legend = dl.select_one("dt")
            perc = dl.select_one("dd.perc span")
            count = dl.select("dd")[-1] if len(dl.select("dd")) > 1 else None
            if legend:
                chart_data[legend.get_text(strip=True)] = {
                    "비율": perc.get_text(strip=True) if perc else None,
                    "인원": count.get_text(strip=True) if count else None
                }

        if chart_data:
            result[chart_key] = chart_data

    return {title: result}
