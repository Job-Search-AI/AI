from src.tools.slices.llm import generate_response as run

def generate_response(user_prompt, documents):
    return run(user_prompt, documents)

if __name__ == "__main__":
    user_prompt = "취업 공고 정보를 분석하고, 취업 공고 정보를 요약해줘."
    documents = "취업 공고 정보: 취업 공고 정보는 취업 공고 정보입니다."
    
    # python -m src.llm.generator
    response = generate_response(user_prompt, documents)
    print(f"응답: {response}")
    
