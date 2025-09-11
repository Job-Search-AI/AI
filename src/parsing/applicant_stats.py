def parse_applicant_stats_text(soup):
    """
    soup = BeautifulSoup(사람인 채용 정보 html, 'html.parser')

    return : str : 지원자 통계 정보 (읽기 편하게 포맷팅)
    """
    stats_section = soup.select_one("div.jv_cont.jv_statics")
    if not stats_section:
        return ""

    lines = []

    # 제목
    title_tag = stats_section.select_one("h2.jv_title")
    title = title_tag.get_text(strip=True) if title_tag else "지원자 통계"
    lines.append(title)
    lines.append("-" * len(title))  # 제목 아래 구분선

    # 전체 지원자 수
    total_dl = stats_section.select_one("dl.total")
    if total_dl:
        dt = total_dl.select_one("dt")
        dd = total_dl.select_one("dd span")
        if dt and dd:
            lines.append(f"{dt.get_text(strip=True)}: {dd.get_text(strip=True)}")
            lines.append("")

    # box_chart 항목들
    charts = stats_section.select("div.box_chart")
    for chart in charts:
        chart_title_tag = chart.select_one("strong.tit_stats")
        if not chart_title_tag:
            continue
        chart_key = chart_title_tag.get_text(strip=True)
        lines.append(chart_key)
        lines.append("-" * len(chart_key))

        chart_data_lines = []

        # bar 형식
        for col in chart.select("div.col"):
            legend = col.select_one("em.legend")
            value = col.select_one("span.value")
            if legend and value:
                chart_data_lines.append(f"  {legend.get_text(strip=True)}: {value.get_text(strip=True)}")

        # donut 차트 형식
        for dl in chart.select("dl"):
            legend = dl.select_one("dt")
            perc = dl.select_one("dd.perc span")
            count = dl.select("dd")[-1] if len(dl.select("dd")) > 1 else None
            if legend:
                perc_text = perc.get_text(strip=True) if perc else "N/A"
                count_text = count.get_text(strip=True) if count else "N/A"
                chart_data_lines.append(f"  {legend.get_text(strip=True)}: 비율 {perc_text}, 인원 {count_text}")

        if chart_data_lines:
            lines.extend(chart_data_lines)
            lines.append("")  # 차트별 구분용 빈 줄

    return "\n".join(lines)
