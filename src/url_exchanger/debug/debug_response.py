#!/usr/bin/env python3
"""
URLExchanger LLM 응답 디버깅
"""

import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.llm.url_exchanger import URLExchanger

def debug_llm_response():
    """LLM 응답을 직접 확인해보기"""
    
    exchanger = URLExchanger()
    
    # 완전한 정보가 있는 테스트 케이스
    test_input = "서울 머신러닝 신입 4년제대학교졸업"
    
    print(f"테스트 입력: {test_input}")
    print("=" * 80)
    
    # LLM 호출
    llm_response = exchanger._call_llm(test_input)
    
    print("LLM 전체 응답:")
    print(llm_response)
    print("=" * 80)
    
    # URL 추출 시도
    extracted_url = exchanger.extract_url_from_response(llm_response)
    print(f"추출된 URL: {extracted_url}")
    
    # 각 라인별로 확인
    print("\n라인별 분석:")
    lines = llm_response.split('\n')
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped:
            print(f"{i+1:2d}: {line_stripped}")
            if 'https://' in line_stripped:
                print(f"    -> URL 후보 발견!")

if __name__ == "__main__":
    debug_llm_response()
