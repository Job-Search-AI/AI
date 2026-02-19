import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from datasets import Dataset
from datasets import load_dataset
import sys
from tqdm import tqdm
import json

from config import PROMPT

_model = None
_tokenizer = None
_device = None

def init_model(model_name="skt/A.X-4.0-Light"):
    global _model, _tokenizer, _device

    # 이미 초기화된 경우
    if _model is not None:
        return

    _device = "cuda" if torch.cuda.is_available() else "cpu"

    # GPU 환경: bitsandbytes 사용, 4비트로 로드
    if _device == "cuda":
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True, # 4비트로 로드
            bnb_4bit_quant_type="nf4", # 4비트 정밀도
            bnb_4bit_compute_dtype=torch.float16, # 컴퓨팅 dtype
            bnb_4bit_use_double_quant=True, 
            bnb_4bit_quant_storage=torch.bfloat16, # 저장 dtype
        )
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            dtype=torch.bfloat16,
            device_map="auto",
        )
    else:
        # CPU 환경: bitsandbytes 없이 로드, float32 사용
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
        )
        _model.to(_device)

    _tokenizer = AutoTokenizer.from_pretrained(model_name)

def get_model():
    return _model, _tokenizer, _device

def extract_url_from_response(llm_response: str) -> Optional[str]:
    """
    LLM 응답에서 최종 URL을 추출
    
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

def generate_response(user_input):
    # query_map.json 로드
    with open("/content/drive/MyDrive/ai_enginner/job_search/AI/src/url_exchanger/query_map.json", 'r', encoding='utf-8') as f:
        query_map = json.load(f)

    # 모델 초기화
    init_model()
    model, tokenizer, device = get_model()

    # 프롬프트 문자열 → 토큰화
    system_content = PROMPT.format(query_field_map=query_map)

    # 모델을 평가 모드로 설정
    model.eval()

    # 채팅 프롬프트 생성
    chat = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_input}
    ]

    # 토큰화
    inputs = tokenizer.apply_chat_template(chat, add_generation_prompt=True, return_tensors="pt").to(device)

    # 추론
    # skip_special_tokens=True: 특수 토큰 제외
    with torch.no_grad():
        output = model.generate(
            inputs,
            max_new_tokens=128,
            do_sample=False,
        )
        len_input_prompt = len(inputs[0])
        response = tokenizer.decode(output[0][len_input_prompt:], skip_special_tokens=True)

    # 응답 반환
    return response

def process_user_input_to_url(user_input):
    response = generate_response(user_input)
    url = extract_url_from_response(response)

    # URL이 추출되지 않았다면
    if not url:
        missing_info = response.strip()

        # 부족한 정보 반환
        return {
            "success": False,
            "url": None,
            "query": user_input,
            "missing_info": missing_info
        }

    # URL이 있으면 성공적으로 반환
    if url:
        return {
            "success": True,
            "url": url,
            "query": user_input,
            "missing_info": None
    }
    else: # URL이 추출되지 않았다면
        return {
            "success": False,
            "url": None,
            "query": user_input,
            "missing_info": "URL을 찾을 수 없습니다."
        }
        