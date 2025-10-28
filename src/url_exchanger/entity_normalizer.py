import json
import os


def load_synonym_dict(synonym_dict_path):
    # synonym_dict.json 파일을 로드하여 유사어 사전을 반환
    with open(synonym_dict_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_entity_value(user_input, synonym_mapping):
    """
    사용자 입력이 유사어 사전에 존재하는지 확인하고, 존재하면 표준값을 반환

    user_input: 사용자 입력값
    user_input = '서울'
    
    synonym_mapping: 유사어 사전
    synonym_mapping = {
        "서울": ["서울", "서울시", "서울특별시", "수도", "강남", "강북", "서울 지역"],
    }

    return: 
    1. 사용자 입력과 유사어 사전을 비교하여 유사어에 존재하면 표준값을 반환
    2. 유사어에 존재하지 않으면 None 반환
    """
    # 사용자 입력값을 유사어 사전과 비교하여 표준값을 반환
    # 대소문자 무시, 공백 제거 등의 전처리 수행
    user_input_normalized = user_input.strip().lower().replace(' ', '')
    
    # 각 표준값과 그에 해당하는 유사어 리스트를 순회
    for standard_value, synonyms in synonym_mapping.items():
        for synonym in synonyms:
            synonym_normalized = synonym.strip().lower().replace(' ', '') # 유사어 정규화
            if user_input_normalized == synonym_normalized:
                return standard_value
    
    return None

def normalize_entities(entities, synonym_dict_path):
    """
    entities: NER로 추출된 entities 딕셔너리
    entities = {
        '지역': '서울',
        '직무': '머신러닝',
        '경력': '1년차',
        '학력': '석사'
    }
    synonym_dict_path: 유사어 사전 파일 경로
    synonym_dict_path = 'synonym_dict.json'
    """ 
    # NER로 추출된 entities 딕셔너리를 받아서 각 항목을 표준화
    # 4가지 항목(지역, 직무, 경력, 학력)에 대해 표준화 수행
    
    """
    synonyms_dict = {
        "지역": {
            "서울": ["서울", "서울시", "서울특별시", "수도", "강남", "강북", "서울 지역"],
        }
    }
    """
    synonym_dict = load_synonym_dict(synonym_dict_path)

    
    normalized_entities = {}
    
    # 사용자 입력이 유사어 사전에 존재하면 표준어 변환후 표준화된 엔티티 객체에 저장, 없으면 None 저장
    # 지역 표준화
    if entities.get('지역'):
        normalized_entities['지역'] = normalize_entity_value(
            entities['지역'], # 엔티티 지역
            synonym_dict['지역'] # 유사어 사전 지역
        )
    else:
        normalized_entities['지역'] = None
    
    # 직무 표준화
    if entities.get('직무'):
        normalized_entities['직무'] = normalize_entity_value(
            entities['직무'], 
            synonym_dict['직무']
        )
    else:
        normalized_entities['직무'] = None
    
    # 경력 표준화
    if entities.get('경력'):
        normalized_entities['경력'] = normalize_entity_value(
            entities['경력'], 
            synonym_dict['경력']
        )
    else:
        normalized_entities['경력'] = None
    
    # 학력 표준화
    if entities.get('학력'):
        normalized_entities['학력'] = normalize_entity_value(
            entities['학력'], 
            synonym_dict['학력']
        )
    else:
        normalized_entities['학력'] = None
    
    return normalized_entities


def check_missing_entities(normalized_entities):
    """
    표준화된 엔티티에서 누락된 항목인 None이 존재하는지 확인

    normalized_entities = {
        '지역': '서울',
        '직무': '머신러닝',
        '경력': '1년차',
        '학력': '석사'
    }

    return 
    1. 누락된 항목이 있으면 누락된 항목 리스트 반환
    ["지역", "직무", "경력", "학력"]
    2. 누락된 항목이 없으면 빈 리스트 반환
    []
    """
    # 표준화된 엔티티에서 누락된 항목 확인
    # 4가지 필수 항목(지역, 직무, 경력, 학력) 중 None인 항목을 찾음
    
    required_fields = ['지역', '직무', '경력', '학력']
    missing_fields = []
    
    for field in required_fields:
        if normalized_entities.get(field) is None:
            missing_fields.append(field)
    
    return missing_fields


def generate_missing_message(missing_fields):
    """
    누락된 항목이 존재하면 재입력 요청 메시지 생성

    missing_fields: 누락된 항목 리스트
    missing_fields = ["지역", "직무", "경력", "학력"]

    return
    1. 누락된 항목이 있으면 재입력 요청 메시지 반환
    """
    # 누락된 항목에 대해 사용자에게 재입력 요청 메시지 생성
    # 각 항목별로 적절한 질문 문구 생성
    
    if not missing_fields:
        return None
    
    questions = []
    
    for field in missing_fields:
        if field == '지역':
            questions.append('근무 희망 지역이 어디신가요?(서울 or 경기)')
        
        if field == '직무':
            questions.append('어떤 직무를 찾고 계신가요?')

        if field == '경력':
            questions.append('신입 또는 경력 몇 년차인가요?')

        if field == '학력':
            questions.append('최종 학력을 알려주실 수 있을까요?')
    
    return '\n'.join(questions)


def normalize_and_validate_entities(entities, synonym_dict_path):
    # 전체 프로세스를 통합하는 메인 함수
    # 1. 엔티티 표준화
    # 2. 누락된 항목 확인
    # 3. 누락된 항목이 있으면 재입력 요청 메시지 반환
    # 4. 모든 항목이 있으면 표준화된 엔티티 반환
    
    # 사용자 입력한 엔티티를 유사어 사전에서 찾아 존재하면 표준화된 엔티티로 변환
    normalized_entities = normalize_entities(entities, synonym_dict_path)
    
    # 표준화된 엔티티에서 누락된 항목 확인
    missing_fields = check_missing_entities(normalized_entities)
    
    if missing_fields:
        message = generate_missing_message(missing_fields)
        return {
            'status': 'incomplete',
            'message': message,
            'missing_fields': missing_fields,
            'normalized_entities': normalized_entities
        }
    
    return {
        'status': 'complete',
        'message': '모든 정보가 확인되었습니다.',
        'normalized_entities': normalized_entities
    }
