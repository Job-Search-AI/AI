import os
import json

def mapping_url_query(entity):
    root_path = os.getenv("JOB_SEARCH_ROOT")
    query_map_path = os.path.join(root_path, 'data', 'url_exchager', 'query_map.json')
    
    with open(query_map_path, 'r', encoding='utf-8') as f:
        query_map_data = json.load(f)

    url_base = 'https://www.saramin.co.kr/zf_user/search?searchType=search?'

    for i, (key, val) in enumerate(entity.items()) :
        if i == 0:
            url_base += query_map_data[key][val]
        else:
            url_base += '&' + query_map_data[key][val]

    url_base += '&edu_none=y&exp_none=y'

    return url_base

if __name__ == '__main__':
    entity = {
        '지역': '서울',
        '직무': '머신러닝',
        '경력': '1년차',
        '학력': '4년제대학교'
    }
    url = mapping_url_query(entity)