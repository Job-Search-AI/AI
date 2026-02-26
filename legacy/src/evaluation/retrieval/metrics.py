def recall_at_k(recommended, relevant, k):
    recommended_at_k = recommended[:k]          # 추천 결과 중 상위 k개만 자름
    relevant_set = set(relevant)                # 정답 문서를 집합으로 변환
    hit_set = set(recommended_at_k) & relevant_set  # 교집합(= top-k 안에서 정답인 문서들)

    if len(relevant_set) == 0:                  # 정답 문서가 없는 경우 (분모=0 방지)
        return 0.0
    return len(hit_set) / len(relevant_set)     # 정답 중 몇 개나 찾았는가?	

def precision_at_k(recommended, relevant, k):
    recommended_at_k = recommended[:k]           # 추천 결과 중 상위 k개만 자름
    relevant_set = set(relevant)                 # 정답 문서를 집합으로 변환
    hit_set = set(recommended_at_k) & relevant_set

    if len(recommended_at_k) == 0:              # 추천 결과가 아예 없으면 precision=0
        return 0.0
    return len(hit_set) / len(recommended_at_k) # top-k 중 정답의 비율


def hit_at_k(recommended, relevant, k):
    recommended_at_k = recommended[:k]          # 추천 결과 중 상위 k개만 자름
    relevant_set = set(relevant)                # 정답 문서를 집합으로 변환
    
    if(set(recommended_at_k) & relevant_set):   # 정답 문서가 추천 결과 중 하나라도 있으면 1.0
        return 1.0
    else:
        return 0.0

