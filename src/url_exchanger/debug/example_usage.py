#!/usr/bin/env python3
"""
URLExchanger 사용 예제

이 스크립트는 URLExchanger 클래스를 사용하여 
사용자 입력을 URL 쿼리로 변환하는 방법을 보여줍니다.
"""

import os
import sys

# 프로젝트 루트 디렉토리를 sys.path에 추가=
project_root = '/content/drive/MyDrive/ai_enginner/job_search/AI/'
sys.path.append(project_root)

from src.llm.url_exchanger import URLExchanger

def interactive_example():
    """대화형 사용 예제"""
    print("=== URLExchanger 대화형 예제 ===")
    print("채용공고 검색 조건을 자연어로 입력해주세요.")
    print("예: '서울 머신러닝 신입 4년제대학교졸업'")
    print("종료하려면 'quit' 또는 'exit'를 입력하세요.\n")
    
    exchanger = URLExchanger()
    
    while True:
        try:
            user_input = input("검색 조건: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '종료']:
                print("프로그램을 종료합니다.")
                break
            
            if not user_input:
                print("검색 조건을 입력해주세요.\n")
                continue
            
            print(f"\n처리 중: {user_input}")
            result = exchanger.process_user_input(user_input)

            print(result)
            
            
            print("-" * 80)
            
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류가 발생했습니다: {e}")


def main():
    """메인 함수"""
    print("URLExchanger 사용 예제\n")
    
    while True:
        print("실행할 예제를 선택하세요:")
        print("1. 대화형 예제")
        print("2. 종료")
        
        choice = input("\n선택 (1-2): ").strip()
        
        if choice == '1':
            interactive_example()
        elif choice == '2':
            print("프로그램을 종료합니다.")
            break
        else:
            print("올바른 번호를 선택해주세요.\n")
        
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
