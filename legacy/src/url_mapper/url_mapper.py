from src.node import mapping_url_query_node


def mapping_url_query(entity):
    # 기존 API는 dict 입력 -> 문자열 URL 반환을 유지하고, 내부 구현만 node로 위임한다.
    result = mapping_url_query_node({"normalized_entities": entity})
    # LangGraph 노드는 partial state를 반환하므로 레거시 API에서는 url 키만 꺼내 반환한다.
    return result["url"]


if __name__ == '__main__':
    # 수동 실행 시에도 레거시 함수 시그니처를 그대로 사용해 회귀를 확인할 수 있다.
    entity = {
        "지역": "서울",
        "직무": "머신러닝",
        "경력": "1년차",
        "학력": "4년제대학교",
    }
    url = mapping_url_query(entity)
