from bs4 import BeautifulSoup

# 코어 경로를 tools로 고정하기 위해 파싱 의존을 src.tools.parsing 내부 구현으로 모은다.
from src.tools.parsing.applicant_stats import parse_applicant_stats_text
from src.tools.parsing.benefit import parse_benefit_text
from src.tools.parsing.company_info import parse_company_info_text
from src.tools.parsing.howto import parse_howto_text
from src.tools.parsing.job_detail import parse_job_detail_text
from src.tools.parsing.location import parse_location_text
from src.tools.parsing.metadata_converter import convert_html_list_to_metadata_list
from src.tools.parsing.summary import parse_summary_text
from src.tools.parsing.title import parse_title_text


def _build_parsed_text(html_content: str) -> str:
    # HTML 하나를 파싱한 뒤 구분선/장식 기호를 제거하고 줄바꿈을 정리한다.
    soup = BeautifulSoup(html_content, "html.parser")
    parts = [
        parse_title_text(soup),
        parse_summary_text(soup),
        parse_benefit_text(soup),
        parse_location_text(soup),
        parse_job_detail_text(soup),
        parse_howto_text(soup),
        parse_applicant_stats_text(soup),
        parse_company_info_text(soup),
    ]

    sections: list[str] = []
    for part in parts:
        if not part:
            continue
        lines = part.splitlines()
        clean_lines: list[str] = []
        last_blank = False
        for raw_line in lines:
            line = raw_line.strip()
            line = line.replace("**", "")
            line = line.replace("---", "")
            line = line.strip()
            if not line:
                if clean_lines and not last_blank:
                    clean_lines.append("")
                last_blank = True
                continue

            only_sep = True
            for char in line:
                if char not in "-*":
                    only_sep = False
                    break
            if only_sep:
                continue

            clean_lines.append(line)
            last_blank = False

        while clean_lines and clean_lines[-1] == "":
            clean_lines.pop()
        if clean_lines:
            sections.append("\n".join(clean_lines))

    return "\n\n".join(sections)


def parsing_job_info(html_contents: list[str]) -> list[str]:
    # I/O 경계에서 타입을 확인해 node/legacy 양쪽에서 동일한 오류를 보장한다.
    if not isinstance(html_contents, list):
        raise ValueError("html_contents must be a list of HTML strings")

    # 각 원소도 문자열인지 확인해 BeautifulSoup 파싱 단계에서 모호한 오류를 막는다.
    if any(not isinstance(html_content, str) for html_content in html_contents):
        raise ValueError("html_contents must contain only HTML strings")

    job_info_list: list[str] = []
    for html_content in html_contents:
        job_info_list.append(_build_parsed_text(html_content))
    return job_info_list


def parsing_job_metadata(
    html_contents: list[str], base_url: str = ""
) -> list[dict[str, object]]:
    # metadata 변환도 같은 입력 계약을 사용해 파싱 API 간 동작을 통일한다.
    if not isinstance(html_contents, list):
        raise ValueError("html_contents must be a list of HTML strings")

    # 메타데이터 변환 함수는 문자열 입력을 기대하므로 사전에 타입을 고정한다.
    if any(not isinstance(html_content, str) for html_content in html_contents):
        raise ValueError("html_contents must contain only HTML strings")

    metadata_list = convert_html_list_to_metadata_list(html_contents, base_url)
    return [dict(metadata) for metadata in metadata_list]


__all__ = ["parsing_job_info", "parsing_job_metadata"]
