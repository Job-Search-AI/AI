"""
채용공고 요약 및 카드형 UI 메타데이터 생성 함수 모듈
"""

import os
import sys
import torch
from typing import List, Dict, Any, Optional
from transformers import BitsAndBytesConfig, AutoModelForCausalLM, AutoTokenizer
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 프로젝트 경로 추가
sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")


# 전역 모델 변수 (메모리 효율성을 위해)
_model = None
_tokenizer = None
_device = None


def initialize_job_summarizer_model(model_name: str = "skt/A.X-4.0-Light"):
    """모델과 토크나이저 초기화 (필수)"""
    global _model, _tokenizer, _device
    
    print(f"LLM 모델 초기화 시작: {model_name}")
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"사용 디바이스: {_device}")
    
    # BitsAndBytes 설정 (메모리 최적화)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_storage=torch.bfloat16,
    )
    
    # 모델 로드
    print("모델 다운로드 및 로드 중...")
    _model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        dtype=torch.bfloat16,
        device_map="auto"
    )
    
    # 토크나이저 로드
    print("토크나이저 로드 중...")
    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token
        
    print(f"LLM 모델 초기화 완료!")
    print(f"   모델: {model_name}")
    print(f"   디바이스: {_device}")
    print(f"   양자화: 4-bit")
    
    return True


def create_job_text_from_data(job_data: Dict[str, Any]) -> str:
    """채용공고 데이터를 텍스트로 변환"""
    text_parts = []
    
    # 기본 정보
    if job_data.get("title"):
        text_parts.append(f"채용공고: {job_data['title']}")
    if job_data.get("company"):
        text_parts.append(f"회사: {job_data['company']}")
    
    # 채용 정보
    if job_data.get("position"):
        text_parts.append(f"직무: {job_data['position']}")
    if job_data.get("experience"):
        text_parts.append(f"경력: {job_data['experience']}")
    if job_data.get("education"):
        text_parts.append(f"학력: {job_data['education']}")
    if job_data.get("location"):
        text_parts.append(f"근무지: {job_data['location']}")
    if job_data.get("salary"):
        text_parts.append(f"급여: {job_data['salary']}")
    
    # 상세 정보
    if job_data.get("description"):
        text_parts.append(f"상세 내용: {job_data['description']}")
    if job_data.get("benefits"):
        text_parts.append(f"복리후생: {job_data['benefits']}")
    
    return "\n".join(text_parts)


def create_summary_prompt(user_query: str, job_text: str) -> str:
    """사용자 쿼리와 채용공고 텍스트를 바탕으로 요약 프롬프트 생성"""
    prompt = f"""다음 채용공고를 사용자의 관심사에 맞춰 요약해주세요.

사용자 질문: {user_query}

채용공고 정보:
{job_text}

만약 사용자의 질문과 관련이 없으면 "요약 없음"을 반환해주세요.

다음 형식으로 요약해주세요:
1. 핵심 포인트 (사용자 질문과 관련된 내용 위주)
2. 주요 자격요건
3. 근무조건 및 혜택
4. 추천도 (1-5점)와 그 이유

요약:"""
    
    return prompt


def generate_job_summary(user_query: str, job_data: Dict[str, Any]) -> str:
    """채용공고 요약 생성 (LLM 전용)"""
    global _model, _tokenizer, _device
    
    if _model is None or _tokenizer is None:
        raise RuntimeError("LLM 모델이 초기화되지 않았습니다. initialize_job_summarizer_model()를 먼저 호출하세요.")
    
    # 채용공고 텍스트 생성
    job_text = create_job_text_from_data(job_data)
    
    # 프롬프트 생성
    prompt = create_summary_prompt(user_query, job_text)
    
    # 토크나이징
    inputs = _tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
    if _device == "cuda":
        inputs = {k: v.to(_device) for k, v in inputs.items()}
    
    # 생성
    with torch.no_grad():
        outputs = _model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=300,
            temperature=0.7,
            do_sample=True,
            pad_token_id=_tokenizer.eos_token_id
        )
    
    # 디코딩
    generated_text = _tokenizer.decode(outputs[0], skip_special_tokens=True)
    summary = generated_text[len(prompt):].strip()
    
    if not summary:
        raise ValueError("LLM이 빈 요약을 생성했습니다.")
    
    return summary




def process_job_for_card_metadata(user_query: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """채용공고를 카드 메타데이터 형식으로 처리"""
    
    # 요약 생성
    summary = generate_job_summary(user_query, job_data)
    
    # 카드 메타데이터 생성
    card_metadata = {
        "id": job_data.get("url", ""),
        "title": job_data.get("title", "제목 없음"),
        "company": job_data.get("company", "회사명 없음"),
        "location": job_data.get("location", "정보 없음"),
        "experience": job_data.get("experience", "정보 없음"),
        "salary": job_data.get("salary", "정보 없음"),
        "employment_type": job_data.get("employment_type", "정보 없음"),
        "summary": summary,
        "description": job_data.get("description", "")[:200] + "..." if len(job_data.get("description", "")) > 200 else job_data.get("description", ""),
        "url": job_data.get("url", ""),
        "match_score": 0.8  # 기본 매칭 점수
    }
    
    return card_metadata


def batch_process_jobs(user_query: str, job_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """여러 채용공고를 LLM으로 배치 처리"""
    results = []
    
    print(f"LLM 배치 처리 시작: {len(job_list)}개 채용공고")
    
    # 모델 초기화 확인
    global _model, _tokenizer
    if _model is None or _tokenizer is None:
        raise RuntimeError("LLM 모델이 초기화되지 않았습니다. initialize_job_summarizer_model()를 먼저 호출하세요.")
    
    for i, job_data in enumerate(job_list, 1):
        print(f"[{i}/{len(job_list)}] LLM 요약 생성 중: {job_data.get('title', '제목없음')}")
        
        # LLM으로 카드 메타데이터 처리 (실패시 예외 발생)
        card_metadata = process_job_for_card_metadata(user_query, job_data)
        results.append(card_metadata)
        
        print(f"[{i}/{len(job_list)}] 완료")
    
    print(f"LLM 배치 처리 완료: {len(results)}개 결과")
    return results


async def async_batch_process_jobs(user_query: str, job_list: List[Dict[str, Any]], 
                                 max_workers: int = 3) -> List[Dict[str, Any]]:
    """비동기 배치 처리"""
    loop = asyncio.get_event_loop()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = []
        for job_data in job_list:
            task = loop.run_in_executor(
                executor, 
                process_job_for_card_metadata, 
                user_query, 
                job_data
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 예외 처리
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"비동기 처리 실패 [{i}]: {result}")
            # 폴백 메타데이터 생성
            fallback = {
                "id": f"job_{i}",
                "title": "처리 실패",
                "company": "정보 없음",
                "summary": "처리 중 오류가 발생했습니다.",
                "match_score": 0.0
            }
            processed_results.append(fallback)
        else:
            processed_results.append(result)
    
    return processed_results


if __name__ == "__main__":
    # 실제 LLM 테스트
    sample_job = {
        "title": "AI/ML 엔지니어",
        "company": "테크 스타트업",
        "location": "서울 강남구",
        "salary": "3000-4000만원",
        "description": "머신러닝 모델 개발 및 배포, 데이터 파이프라인 구축",
        "benefits": "재택근무 가능, 교육비 지원",
        "url": "https://example.com/job/123"
    }
    
    print("실제 LLM 모델 테스트")
    user_query = "서울 신입 대졸 nlp개발자"
    
    # 모델 초기화
    initialize_job_summarizer_model()
    
    # LLM 요약 생성
    result = process_job_for_card_metadata(user_query, sample_job)
    print("LLM 생성 카드 메타데이터:")
    for key, value in result.items():
        print(f"{key}: {value}")
            

