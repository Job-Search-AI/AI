from transformers import BitsAndBytesConfig, AutoModelForCausalLM, AutoTokenizer
import torch
from ..utils import get_device, print_device_info

def generate_response(user_prompt, documents, device_preference="auto"):
    """
    LLM을 사용하여 응답을 생성하는 함수
    
    Args:
        user_prompt (str): 사용자 프롬프트
        documents (str): 분석할 문서
        device_preference (str): "auto", "cuda", "mps", "cpu" 중 선택
        
    Returns:
        str: 생성된 응답
    """
    # device 선택
    device = get_device(device_preference)
    print_device_info(device)
    
    # 모델, 토크나이저 로드
    model_name = "skt/A.X-4.0-Light"

    # device에 따른 설정 조정
    if device == "cuda":
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
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
    else:
        # CPU나 MPS의 경우 4bit 양자화 없이 로드
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32 if device == "cpu" else torch.float16,
            device_map="auto"
        )

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # instruct와 user 메시지 생성
    chat = [
        {"role": "system", "content": "너는 취업 공고 정보 분석 전문가야. 취업 공고 정보를 분석하고, 취업 공고 정보를 요약하는 것이 너의 일이야.\n제공된 취업 공고 정보:\n" + documents},
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
    
    # device에 맞게 입력 이동
    if device != "auto":
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
    
    # device 선택 예시
    print("=== Device 선택 예시 ===")
    print("1. 자동 선택 (권장)")
    response = generate_response(user_prompt, documents, "auto")
    print(f"응답: {response}")
    
    print("\n2. CPU 강제 사용")
    response = generate_response(user_prompt, documents, "cpu")
    print(f"응답: {response}")


