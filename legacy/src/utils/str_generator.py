def dict_to_str(documents):
    """
    딕셔너리를 문자열로 변환하는 함수
    
    Args:
        documents (list:dict): 딕셔너리 리스트
        
    Returns:
        list: 문자열 리스트
        
    Examples:
        >>> documents = [
            {"회사명": "사이트", "채용제목": "채용제목", "직무분야": "직무분야"},
            {"회사명": "사이트", "채용제목": "채용제목", "직무분야": "직무분야"},
        ]
        >>> dict_to_str(documents)
        ['회사명: 사이트 | 채용제목: 채용제목 | 직무분야: 직무분야', '회사명: 사이트 | 채용제목: 채용제목 | 직무분야: 직무분야']
    """
    if documents and isinstance(documents[0], dict):
        # 딕셔너리를 문자열로 변환 (회사명, 채용제목, 직무분야 등을 조합)
        document_strings = []
        for doc in documents:
            # 딕셔너리의 모든 키-값 쌍을 "키: 값" 형태로 조합
            doc_parts = [f"{key}: {value}" for key, value in doc.items() if value]
            doc_str = " | ".join(doc_parts)
            document_strings.append(doc_str)
        return document_strings
    else:
        # 이미 문자열 리스트인 경우
        return documents