import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from src.state import Reply

def generate_response(user_prompt, documents):
    """
    LLM을 사용하여 응답을 생성하는 함수
    
    Args:
        user_prompt (str): 사용자 프롬프트
        documents (list: [str, str, ...]): 분석할 문서
    
    Examples:
        user_prompt = "모집된 공고 축약해줘."
        documents = [
            "\n\n".join([
                "*" * 10,
                "회사명: 사이트 | 채용제목: 채용제목 | 직무분야: 직무분야",
                "*" * 10,
            ]),
            "\n\n".join([
                "*" * 10,
                "회사명: 사이트 | 채용제목: 채용제목 | 직무분야: 직무분야",
                "*" * 10,
            ]),
        ]
    
    Returns:
        str: 생성된 응답
    """
    root_path = os.getenv("JOB_SEARCH_ROOT")
    if not root_path:
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    load_dotenv(os.path.join(root_path, ".env"))
    use_openai = os.getenv("USE_OPENAI_MODELS", "false").lower() == "true"

    documents = "\n\n".join(documents)

    if use_openai:
        timeout = os.getenv("OPENAI_TIMEOUT_SECONDS")
        retries = os.getenv("OPENAI_MAX_RETRIES")
        sec = 120.0
        if timeout:
            sec = float(timeout)
        if sec < 120.0:
            sec = 120.0
        llm = ChatOpenAI(
            model=os.getenv("RESPONSE_MODEL_NAME", "gpt-5-nano"),
            timeout=sec,
            max_retries=int(retries) if retries else None,
        )
        prompt = "\n".join(
            [
                "너는 취업 공고 정보 분석 전문가다.",
                "아래 문서를 바탕으로 사용자 질문에 맞는 답변만 작성한다.",
                "응답은 가독성이 좋게 문단을 나눠 작성한다.",
                "토픽이 바뀌면 한 줄만 띄워 구분한다.",
                "**, --- 같은 장식 기호는 쓰지 않는다.",
                "문서:",
                documents,
                "질문:",
                user_prompt,
            ]
        )
        result = llm.with_structured_output(
            Reply,
            method="json_schema",
            strict=True,
        ).invoke(prompt)
        return result.response

    # device 선택
    device = "cuda"

    import torch
    from transformers import BitsAndBytesConfig, AutoModelForCausalLM, AutoTokenizer
    
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

    # instruct와 user 메시지 생성

    system_msg = "\n".join(
        [
            "너는 취업 공고 정보 분석 전문가야.",
            "취업 공고 정보를 분석하고 요약하는 것이 너의 일이야.",
            "응답은 가독성이 좋게 문단을 나눠 작성해.",
            "토픽이 바뀌면 한 줄만 띄워 구분해.",
            "**, --- 같은 장식 기호는 쓰지 마.",
            "제공된 취업 공고 정보:",
            documents,
        ]
    )
    chat = [
        {"role": "system", "content": system_msg},
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

    return Reply(response=response).response

if __name__ == "__main__":
    user_prompt = "취업 공고 정보를 분석하고, 취업 공고 정보를 요약해줘."
    documents = "취업 공고 정보: 취업 공고 정보는 취업 공고 정보입니다."
    
    # python -m src.llm.generator
    response = generate_response(user_prompt, documents)
    print(f"응답: {response}")
    
