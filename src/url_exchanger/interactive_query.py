import os
import sys
from typing import Dict, Any, Optional, Tuple

# 프로젝트 루트 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.append(project_root)

from src.url_exchaging.url_exchanger import process_user_input_to_url

def interactive_query_handler(initial_query: Optional[str] = None, max_iterations: int = 3) -> Dict[str, Any]:
    """
    사용자와 대화형으로 상호작용하여 완전한 검색 URL을 생성합니다.
    
    Args:
        initial_query: 사용자의 초기 질문
        max_iterations: 최대 반복 횟수
        
    Returns:
        최종 결과 딕셔너리
        - success: 성공 여부
        - url: 생성된 URL (성공 시)
        - conversation: 대화 기록
        - error: 오류 메시지 (실패 시)
    """
    conversation = []
    current_query = (initial_query or "").strip()

    # 초기 입력이 없으면 함수 내부에서 사용자에게 입력을 요청
    if not current_query:
        while True:
            user_input = input("검색 조건을 입력하세요: ").strip()
            if user_input:
                current_query = user_input
                initial_query = user_input
                break
            print("❌ 검색 조건을 입력해주세요.")

    print(f"사용자 입력: {current_query}")
    conversation.append({"role": "user", "content": current_query})
    
    for iteration in range(max_iterations):
        print(f"--- 시도 {iteration + 1}/{max_iterations} ---")
        
        # URL 생성 시도
        result = process_user_input_to_url(current_query)
        
        if result['success']:
            # 성공적으로 URL 생성됨
            print("✅ URL 생성 성공!")
            print(f"최종 URL: {result['url']}")
            
            conversation.append({
                "role": "assistant", 
                "content": f"URL 생성 완료: {result['url']}"
            })
            
            return result['url'], current_query  
        
        elif result.get('missing_info'):
            # 부족한 정보가 있음 - 사용자에게 추가 질문
            missing_info = result['missing_info']
            print(f"추가 정보가 필요합니다:")
            print(f"   {missing_info}")
            
            conversation.append({
                "role": "assistant", 
                "content": missing_info
            })
            
            # 사용자로부터 추가 정보 입력받기
            if iteration < max_iterations - 1:  # 마지막 반복이 아닌 경우만
                additional_info = input("추가 정보를 입력해주세요: ").strip()
                
                if not additional_info:
                    print("❌ 추가 정보가 입력되지 않았습니다.")
                    break
                
                conversation.append({"role": "user", "content": additional_info})
                
                # 기존 쿼리와 추가 정보를 결합
                current_query = f"{initial_query} {additional_info}"
                print(f"업데이트된 쿼리: {current_query}")
            else:
                print("❌ 최대 반복 횟수에 도달했습니다.")
                break
        
        else:
            # 기타 오류
            error_msg = result.get('error', '알 수 없는 오류가 발생했습니다.')
            print(f"❌ 오류 발생: {error_msg}")
            
            conversation.append({
                "role": "assistant", 
                "content": f"오류: {error_msg}"
            })
            break
    
    # 실패한 경우
    print("❌ URL 생성 실패")
    exit(1)


if __name__ == "__main__":
    print("=== 대화형 채용공고 검색 실행 ===")
    result = interactive_query_handler()

