#!/usr/bin/env python3
"""
부족한 정보 감지 로직 테스트
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.llm.url_exchanger import URLExchanger

def test_missing_info_detection():
    """부족한 정보 감지 테스트"""
    
    # URLExchanger 인스턴스 생성
    try:
        exchanger = URLExchanger()
    except Exception as e:
        print(f"URLExchanger 초기화 실패: {e}")
        return
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "테스트 1: 경력과 학력 정보 누락",
            "input": "서울 ai 엔지니어",
            "expected_missing": ["경력", "학력"]
        },
        {
            "name": "테스트 2: 지역과 학력 정보 누락", 
            "input": "ai 엔지니어 신입",
            "expected_missing": ["지역", "학력"]
        },
        {
            "name": "테스트 3: 직무와 학력 세부사항 누락",
            "input": "서울 신입 대졸",
            "expected_missing": ["직무", "학력"]
        },
        {
            "name": "테스트 4: 모든 필수 정보 완전",
            "input": "서울 머신러닝 신입 4년제대학교졸업",
            "expected_missing": []
        }
    ]
    
    print("=" * 80)
    print("부족한 정보 감지 로직 테스트")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        print(f"입력: '{test_case['input']}'")
        
        try:
            result = exchanger.process_user_input(test_case['input'])
            
            if result['success']:
                print("✅ 성공: 모든 정보가 완전하여 URL이 생성되었습니다.")
                print(f"{result['url']}")
            else:
                print("✅ 성공: 필수 정보 부족으로 URL 생성을 거부했습니다.")
                if result.get('missing_info'):
                    print(f"{result['missing_info']}")
                else:
                    print(f"오류: {result.get('error')}")
            
            print("LLM 전1체 응답:")
            print(result.get('response', 'N/A'))
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        
        print("-" * 80)

if __name__ == "__main__":
    test_missing_info_detection()
