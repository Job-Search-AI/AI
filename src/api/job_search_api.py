"""
채용공고 검색 API 엔드포인트
프론트엔드와 연동하여 사용자 질의를 처리하고 부족한 정보에 대한 추가 질문을 처리합니다.
"""

import os
import sys
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 프로젝트 루트 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.append(project_root)

from src.url_exchanger.url_exchanger import process_user_input_to_url

app = FastAPI(title="Job Search AI API", version="1.0.0")

# 요청 데이터 형태를 정의
class UserQueryRequest(BaseModel):
    query: str                           # 사용자가 입력한 질문 (필수)
    conversation_id: Optional[str] = None # 대화 세션 ID (선택사항)
    additional_info: Optional[str] = None # 추가 정보 (선택사항)


# 응답 데이터 형태를 정의
class JobSearchResponse(BaseModel):
    success: bool                    # 성공 여부
    conversation_id: str             # 대화 세션 ID
    response_type: str              # 응답 종류 ("url_generated", "need_more_info", "error")
    data: Optional[Dict[str, Any]] = None  # 응답 데이터 (선택사항)
    message: Optional[str] = None    # 메시지 (선택사항)

# 대화 세션 저장소 (실제로는 데이터베이스 사용)
conversation_sessions = {}

def generate_conversation_id() -> str:
    """새로운 대화방 ID 생성"""
    import uuid
    return str(uuid.uuid4())

def get_or_create_session(conversation_id: Optional[str]) -> Dict[str, Any]:
    """대화방을 가져오거나 새로 만듭니다"""
    if not conversation_id:
        conversation_id = generate_conversation_id() # ID가 없으면 새로 만듦
    
    if conversation_id not in conversation_sessions:
        # 새로운 대화방 정보를 만듭니다
        conversation_sessions[conversation_id] = {
            "id": conversation_id,
            "initial_query": "",           # 처음 질문
            "conversation_history": [],    # 대화 기록
            "iteration_count": 0,          # 질문한 횟수
            "max_iterations": 3            # 최대 질문 가능 횟수
        }
    
    return conversation_sessions[conversation_id]

@app.post("/api/search/query", response_model=JobSearchResponse)
def process_user_query(request: UserQueryRequest) -> JobSearchResponse:
    """
    사용자 질의를 처리하여 채용공고 검색 URL을 생성하거나 추가 정보를 요청합니다.
    
    Args:
        request: 사용자 질의 요청
        
    Returns:
        JobSearchResponse: 처리 결과
    """
    try:
        # 대화방 가져오기 또는 생성
        session = get_or_create_session(request.conversation_id)
        
        # 현재 쿼리 설정
        if not session["initial_query"]: # 첫 질문이라면
            # 첫 번째 질의
            session["initial_query"] = request.query # 처음 질문 저장
            current_query = request.query            # 사용할 질문
        else: # 추가 정보가 있는가?
            # 추가 정보가 있는 경우 기존 쿼리와 결합
            if request.additional_info: # 추가 정보가 있다면
                current_query = f"{session['initial_query']} {request.additional_info}"
                session["conversation_history"].append({
                    "role": "user",
                    "content": request.additional_info
                })
            else:
                current_query = session["initial_query"]
        
        # 대화 기록에 추가
        if session["iteration_count"] == 0:
            session["conversation_history"].append({
                "role": "user",
                "content": request.query
            })
        
        # 최대 반복 횟수 체크
        if session["iteration_count"] >= session["max_iterations"]:
            # 3번 넘게 질문했으면 에러 응답
            return JobSearchResponse(
                success=False,
                conversation_id=session["id"],
                response_type="error",
                message="최대 질문 횟수를 초과했습니다. 새로운 검색을 시작해주세요."
            )
        
        # URL 생성 시도
        result = process_user_input_to_url(current_query) # URL 생성 함수 호출
        session["iteration_count"] += 1 # 질문 횟수 증가
        
        if result['success']:
            # 성공적으로 URL 생성됨
            session["conversation_history"].append({
                "role": "assistant",
                "content": f"검색 URL이 생성되었습니다."
            })
            
            return JobSearchResponse(
                success=True,
                conversation_id=session["id"],
                response_type="url_generated",
                data={
                    "url": result['url'],
                    "query": current_query,
                    "conversation_history": session["conversation_history"]
                },
                message="검색 URL이 성공적으로 생성되었습니다."
            )
        
        elif result.get('missing_info'):
            # 부족한 정보가 있음 - 사용자에게 추가 질문
            missing_info = result['missing_info']
            
            session["conversation_history"].append({
                "role": "assistant",
                "content": missing_info
            })
            
            return JobSearchResponse(
                success=True,
                conversation_id=session["id"],
                response_type="need_more_info",
                data={
                    "question": missing_info,
                    "conversation_history": session["conversation_history"],
                    "remaining_attempts": session["max_iterations"] - session["iteration_count"]
                },
                message="추가 정보가 필요합니다."
            )
        
        else:
            # 기타 오류
            error_msg = result.get('error', '알 수 없는 오류가 발생했습니다.')
            
            session["conversation_history"].append({
                "role": "assistant",
                "content": f"오류: {error_msg}"
            })
            
            return JobSearchResponse(
                success=False,
                conversation_id=session["id"],
                response_type="error",
                data={
                    "conversation_history": session["conversation_history"]
                },
                message=error_msg
            )
    
    except Exception as e:
        return JobSearchResponse(
            success=False,
            conversation_id=request.conversation_id or "unknown",
            response_type="error",
            message=f"서버 오류가 발생했습니다: {str(e)}"
        )

@app.post("/api/search/reset")
def reset_conversation(conversation_id: str) -> Dict[str, str]:
    """
    특정 대화방의 정보를 삭제
    
    Args:
        conversation_id: 삭제할 대화 세션 ID
        
    Returns:
        삭제 결과 메시지
    """
    if conversation_id in conversation_sessions:
        del conversation_sessions[conversation_id]
        return {"message": "대화 세션이 삭제되었습니다.", "conversation_id": conversation_id}
    else:
        return {"message": "해당 대화 세션을 찾을 수 없습니다.", "conversation_id": conversation_id}

@app.get("/api/search/session/{conversation_id}")
def get_conversation_session(conversation_id: str) -> Dict[str, Any]:
    """
    특정 대화방의 정보를 조회
    
    Args:
        conversation_id: 조회할 대화방 ID
        
    Returns:
        대화방 정보
    """
    if conversation_id in conversation_sessions:
        return conversation_sessions[conversation_id]
    else:
        raise HTTPException(status_code=404, detail="해당 대화방을 찾을 수 없습니다.")

@app.get("/api/health")
def health_check() -> Dict[str, str]:
    """API 상태 확인"""
    return {"status": "healthy", "message": "Job Search AI API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) # 8000번 포트로 서버 실행
