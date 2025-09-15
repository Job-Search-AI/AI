import json
import os
import sys
from typing import Dict, Any, Optional
import torch
from transformers import BitsAndBytesConfig, AutoModelForCausalLM, AutoTokenizer

# 프로젝트 루트 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.append(project_root)

from config import PROMPT

class URLExchanger:
    """
    사용자 입력을 URL 쿼리로 맵핑하여 최종 URL을 생성하는 클래스
    query_map.json을 기반으로 사용자 입력을 분석하고 적절한 URL 쿼리를 생성합니다.
    """
    
    def __init__(self, query_map_path: str = None, model_name: str = "skt/A.X-4.0-Light"):
        """
        URLExchanger 초기화
        
        Args:
            query_map_path: query_map.json 파일 경로
            model_name: 사용할 허깅페이스 모델 이름
        """
        if query_map_path is None:
            # 현재 파일과 같은 디렉토리에서 query_map.json 찾기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            query_map_path = os.path.join(current_dir, 'query_map.json')
        
        self.query_map_path = query_map_path
        self.query_map = self._load_query_map()
        self.model_name = model_name

        # 모델/토크나이저 로드 (CUDA가 있을 때만 4-bit 양자화 사용)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cuda":
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_storage=torch.bfloat16,
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=bnb_config,
                dtype=torch.bfloat16,
                device_map="auto",
            )
        else:
            # CPU 환경: bitsandbytes 없이 로드, float32 사용
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float32,
            )
            self.model.to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
    def _load_query_map(self) -> Dict[str, Any]:
        """query_map.json 파일을 로드합니다."""
        try:
            with open(self.query_map_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"query_map.json 파일을 찾을 수 없습니다: {self.query_map_path}")
        except json.JSONDecodeError:
            raise ValueError("query_map.json 파일 형식이 올바르지 않습니다.")
    
    def _format_query_map_for_prompt(self) -> str:
        """프롬프트에 사용할 수 있도록 query_map을 문자열로 포맷팅합니다."""
        formatted_map = []
        for query in self.query_map.get('queries', []):
            description = query.get('description', '')
            key = query.get('key', '')
            values = query.get('value', {})
            
            formatted_map.append(f"- {description} ({key}):")
            for k, v in values.items():
                formatted_map.append(f"  * {k}: {v}")
            formatted_map.append("")
        
        return "\n".join(formatted_map)
    
    def _call_llm(self, user_input: str) -> str:
        """
        허깅페이스 모델을 호출하여 사용자 입력을 분석하고 URL 쿼리를 생성합니다.
        
        Args:
            user_input: 사용자 입력 텍스트
            
        Returns:
            LLM 응답 텍스트
        """
        query_field_map = self._format_query_map_for_prompt()
        # 시스템 프롬프트에 템플릿을 그대로 포함하고, 유저 메시지에는 동일 입력을 전달
        system_content = PROMPT.format(query_field_map=query_field_map)

        chat = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_input},
        ]

        # 토큰화 및 디바이스 이동
        inputs = self.tokenizer.apply_chat_template(
            chat,
            add_generation_prompt=True,
            skip_reasoning=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # 생성
        output_ids = self.model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.2,
            top_p=0.6,
            repetition_penalty=1.05,
            tokenizer=self.tokenizer,
        )

        # 입력 길이만큼 잘라서 응답만 디코딩
        # apply_chat_template의 반환 딕셔너리에서 input_ids를 사용
        input_len = inputs["input_ids"].shape[1]
        response_text = self.tokenizer.decode(
            output_ids[0][input_len:], skip_special_tokens=True
        )
        return response_text
    
    def extract_url_from_response(self, llm_response: str) -> Optional[str]:
        """
        LLM 응답에서 최종 URL을 추출합니다.
        
        Args:
            llm_response: LLM 응답 텍스트
            
        Returns:
            추출된 URL 또는 None
        """
        lines = llm_response.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 완전한 URL이 한 줄에 있는 경우
            if line.startswith('https://www.saramin.co.kr/zf_user/jobs/list/domestic?') and '&' in line:
                url = line.replace('&amp;', '&')
                return url
        
        return None
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        사용자 입력을 처리하여 URL을 생성합니다.
        
        Args:
            user_input: 사용자 입력 텍스트
            
        Returns:
            처리 결과를 담은 딕셔너리
            - success: 성공 여부
            - url: 생성된 URL (성공 시)
            - response: LLM 전체 응답
            - missing_info: 부족한 정보 (있는 경우)
            - error: 오류 메시지 (실패 시)
        """
        try:
            # LLM 호출
            llm_response = self._call_llm(user_input)
            
            # URL 추출 시도
            final_url = self.extract_url_from_response(llm_response)
            
            # URL이 없으면 부족한 정보로 간주 (새로운 간단한 프롬프트 기준)
            missing_info = None
            if not final_url:
                # LLM 응답 전체를 부족한 정보로 처리 (URL이 아닌 경우)
                missing_info = llm_response.strip()
            
            # 만약 부족한 정보가 있다면, URL을 생성하지 않고 바로 반환
            if missing_info:
                return {
                    'success': False,
                    'response': llm_response,
                    'missing_info': missing_info,
                    'error': '필수 정보가 부족합니다. 추가 정보를 제공해주세요.'
                }
            
            # URL이 있으면 성공적으로 반환  
            if final_url:
                return {
                    'success': True,
                    'response': llm_response,
                    'url': final_url,
                    'missing_info': None
                }
            else:
                return {
                    'success': False,
                    'response': llm_response,
                    'missing_info': None,
                    'error': '최종 URL을 생성할 수 없습니다.'
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': None,
                'missing_info': None
            }
    
    def get_url_only(self, user_input: str) -> str:
        """
        사용자 입력을 처리하여 URL만 반환합니다.
        
        Args:
            user_input: 사용자 입력 텍스트
            
        Returns:
            생성된 URL 문자열 또는 오류 메시지
        """
        result = self.process_user_input(user_input)
        
        if result['success']:
            return result['url']
        else:
            return f"추가 정보 필요: {result['llm_response']}"

def main():
    """테스트용 메인 함수"""
    exchanger = URLExchanger()
    
    # 테스트 케이스들
    test_cases = [
        "서울 머신러닝 신입 4년제대학교졸업",
        "경기 데이터분석가 3년차 정규직 석사졸업",
        "딥러닝 박사졸업 경력무관 계약직",
        "서울에서 AI 관련 신입 채용 공고"
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n=== 테스트 케이스 {i} ===")
        print(f"입력: {test_input}")
        
        result = exchanger.process_user_input(test_input)
        
        if result['success']:
            print(f"✅ 성공!")
            print(f"URL: {result['url']}")
        else:
            print(f"❌ 실패: {result.get('error', '알 수 없는 오류')}")
            if result.get('missing_info'):
                print(f"부족한 정보: {result['missing_info']}")
        
        print(f"\nLLM 응답:\n{result['response']}")
        print("-" * 80)


if __name__ == "__main__":
    main()