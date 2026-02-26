"""URL 매핑 공개 함수를 패키지 루트에서 바로 노출한다."""

from .url_mapper import mapping_url_query

__all__ = ["mapping_url_query"]
