from typing import TypedDict


class CrawlingState(TypedDict, total=False):
    url: str
    max_jobs: int
    html_contents: list[str]
    crawled_count: int
