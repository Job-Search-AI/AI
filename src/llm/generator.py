import os
import sys

# 단독으로 이 파일을 실행시, 아래 두 주석을 풀어야 모델이 캐쉬에 저장된다.
# 아래 두 주석은 transformers 라이브러리 import 보다 위에 존재해야한다.
# cache_dir = '/content/drive/MyDrive/ai_enginner/job_search/AI/cache/'
# os.environ['HF_HOME'] = cache_dir

import torch
from transformers import BitsAndBytesConfig, AutoModelForCausalLM, AutoTokenizer

def generate_response(user_prompt, documents):
    """
    LLM을 사용하여 응답을 생성하는 함수
    
    Args:
        user_prompt (str): 사용자 프롬프트
        documents (list: [dict, dict, ...]): 분석할 문서
    
    Examples:
        user_prompt = "모집된 공고 축약해줘."
        documents = [
            {"회사명": "사이트", "채용제목": "채용제목", "직무분야": "직무분야"},
            {"회사명": "사이트", "채용제목": "채용제목", "직무분야": "직무분야"},
        ]
    
    Returns:
        str: 생성된 응답
    """
    # device 선택
    device = "cuda"
    
    # 모델, 토크나이저 로드
    model_name = "skt/A.X-4.0-Light"

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_storage=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        dtype=torch.bfloat16,
        device_map="auto"
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # docs 문자열로 변환 
    str_documents = ''
    
    for i, doc_obj in enumerate(documents):
        str_documents += f'[{i}] \n '
        for key, value in doc_obj.items():
            str_documents += f'{key}: {value} | '
        str_documents += '\n'

    # instruct와 user 메시지 생성
    chat = [
        {"role": "system", "content": "너는 취업 공고 정보 분석 전문가야. 취업 공고 정보를 분석하고, 취업 공고 정보를 요약하는 것이 너의 일이야.\n제공된 취업 공고 정보:\n" + str_documents},
        {"role": "user", "content": user_prompt}
    ]

    # 메시지 토큰화
    inputs = tokenizer.apply_chat_template(
                chat,
                add_generation_prompt=True,
                skip_reasoning=True,
                return_dict=True,
                return_tensors="pt"
            )
    
    inputs = inputs.to(device)

    output_ids = model.generate(
        **inputs,
        max_length=1024,
        do_sample=True,
        stop_strings=["<|endofturn|>", "<|stop|>"],
        temperature=0.5,
        top_p=0.6,
        repetition_penalty=1.05,
        tokenizer=tokenizer
    )

    len_input_prompt = len(inputs[0])
    response = tokenizer.decode(output_ids[0][len_input_prompt:], skip_special_tokens=True)

    return response

if __name__ == "__main__":
    user_prompt = "취업 공고 정보를 분석하고, 취업 공고 정보를 요약해줘."
    documents = "취업 공고 정보: 취업 공고 정보는 취업 공고 정보입니다."
    
    # python -m src.llm.generator
    response = generate_response(user_prompt, documents)
    print(f"응답: {response}")
    

