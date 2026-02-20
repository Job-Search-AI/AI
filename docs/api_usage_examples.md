# Job Search AI API 사용법 가이드

## 개요

이 API는 프론트엔드와 백엔드 간의 채용공고 검색 서비스를 위한 인터페이스입니다. 사용자의 자연어 질의를 처리하고, 부족한 정보가 있을 경우 추가 질문을 통해 완전한 검색 조건을 수집합니다.

## API 엔드포인트

### 1. 사용자 질의 처리
**POST** `/api/search/query`

사용자의 질의를 처리하여 검색 URL을 생성하거나 추가 정보를 요청합니다.

#### 요청 형식
```json
{
  "query": "서울에서 AI 엔지니어 신입 채용",
  "conversation_id": "optional-session-id",
  "additional_info": "추가 정보 (선택사항)"
}
```

#### 응답 형식
```json
{
  "success": true,
  "conversation_id": "uuid-string",
  "response_type": "url_generated|need_more_info|error",
  "data": {
    "url": "생성된 검색 URL",
    "query": "처리된 쿼리",
    "conversation_history": []
  },
  "message": "응답 메시지"
}
```

### 2. 대화 세션 초기화
**POST** `/api/search/reset`

기존 대화 세션을 초기화합니다.

#### 요청 형식
```json
{
  "conversation_id": "session-id-to-reset"
}
```

### 3. 대화 세션 조회
**GET** `/api/search/session/{conversation_id}`

특정 대화 세션의 정보를 조회합니다.

### 4. 헬스 체크
**GET** `/api/health`

API 서버 상태를 확인합니다.

## 사용 시나리오 예제

### 시나리오 1: 완전한 정보가 포함된 질의

**1단계: 초기 질의**
```javascript
// 프론트엔드에서 API 호출
const response = await fetch('/api/search/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: "서울에서 AI 엔지니어 신입 채용 연봉 4000만원 이상"
  })
});

const result = await response.json();
```

**예상 응답:**
```json
{
  "success": true,
  "conversation_id": "abc-123-def",
  "response_type": "url_generated",
  "data": {
    "url": "https://www.saramin.co.kr/zf_user/search/recruit?searchType=search&searchword=AI+엔지니어&loc_mcd=101000&exp_cd=1&sal_cd=4000",
    "query": "서울에서 AI 엔지니어 신입 채용 연봉 4000만원 이상",
    "conversation_history": [
      {"role": "user", "content": "서울에서 AI 엔지니어 신입 채용 연봉 4000만원 이상"},
      {"role": "assistant", "content": "검색 URL이 생성되었습니다."}
    ]
  },
  "message": "검색 URL이 성공적으로 생성되었습니다."
}
```

### 시나리오 2: 부족한 정보로 인한 추가 질문

**1단계: 초기 질의 (정보 부족)**
```javascript
const response = await fetch('/api/search/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: "AI 엔지니어 채용"
  })
});
```

**예상 응답:**
```json
{
  "success": true,
  "conversation_id": "abc-123-def",
  "response_type": "need_more_info",
  "data": {
    "question": "근무 희망 지역을 알려주세요. (예: 서울, 경기, 부산 등)",
    "conversation_history": [
      {"role": "user", "content": "AI 엔지니어 채용"},
      {"role": "assistant", "content": "근무 희망 지역을 알려주세요. (예: 서울, 경기, 부산 등)"}
    ],
    "remaining_attempts": 2
  },
  "message": "추가 정보가 필요합니다."
}
```

**2단계: 추가 정보 제공**
```javascript
const response2 = await fetch('/api/search/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: "AI 엔지니어 채용",
    conversation_id: "abc-123-def",
    additional_info: "서울"
  })
});
```

**예상 응답:**
```json
{
  "success": true,
  "conversation_id": "abc-123-def",
  "response_type": "need_more_info",
  "data": {
    "question": "경력 조건을 알려주세요. (예: 신입, 1년 이상, 3년 이상 등)",
    "conversation_history": [
      {"role": "user", "content": "AI 엔지니어 채용"},
      {"role": "assistant", "content": "근무 희망 지역을 알려주세요. (예: 서울, 경기, 부산 등)"},
      {"role": "user", "content": "서울"},
      {"role": "assistant", "content": "경력 조건을 알려주세요. (예: 신입, 1년 이상, 3년 이상 등)"}
    ],
    "remaining_attempts": 1
  },
  "message": "추가 정보가 필요합니다."
}
```

## 프론트엔드 구현 예제

### React 컴포넌트 예제

```javascript
import React, { useState } from 'react';

function JobSearchComponent() {
  const [query, setQuery] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (userInput) => {
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/search/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: conversationId ? query : userInput,
          conversation_id: conversationId,
          additional_info: conversationId ? userInput : null
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setConversationId(result.conversation_id);
        
        if (result.response_type === 'url_generated') {
          // URL 생성 성공 - 검색 결과 페이지로 이동하거나 크롤링 시작
          console.log('Generated URL:', result.data.url);
          setMessages(result.data.conversation_history);
        } else if (result.response_type === 'need_more_info') {
          // 추가 정보 필요 - 사용자에게 질문 표시
          setMessages(result.data.conversation_history);
        }
      } else {
        // 오류 처리
        console.error('Error:', result.message);
      }
    } catch (error) {
      console.error('API call failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const resetConversation = async () => {
    if (conversationId) {
      await fetch('/api/search/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: conversationId
        })
      });
    }
    
    setConversationId(null);
    setMessages([]);
    setQuery('');
  };

  return (
    <div>
      <div className="conversation-history">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <strong>{msg.role === 'user' ? '사용자' : 'AI'}:</strong> {msg.content}
          </div>
        ))}
      </div>
      
      <div className="input-section">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="채용공고 검색 조건을 입력하세요..."
          disabled={isLoading}
        />
        <button 
          onClick={() => handleSubmit(query)} 
          disabled={isLoading || !query.trim()}
        >
          {isLoading ? '처리중...' : '검색'}
        </button>
        <button onClick={resetConversation}>
          새로운 검색
        </button>
      </div>
    </div>
  );
}

export default JobSearchComponent;
```

## 응답 타입별 처리 방법

### 1. `url_generated` 타입
- 검색 URL이 성공적으로 생성됨
- `data.url`을 사용하여 크롤링 프로세스 시작
- 사용자에게 검색 진행 상황 표시

### 2. `need_more_info` 타입
- 추가 정보가 필요함
- `data.question`을 사용자에게 표시
- 사용자 입력을 받아 `additional_info`로 재전송

### 3. `error` 타입
- 오류 발생
- `message`를 사용자에게 표시
- 필요시 대화 세션 초기화

## 주의사항

1. **세션 관리**: `conversation_id`를 적절히 관리하여 대화 연속성 유지
2. **최대 반복 횟수**: 3회 제한으로 무한 루프 방지
3. **오류 처리**: 네트워크 오류, 서버 오류에 대한 적절한 처리
4. **사용자 경험**: 로딩 상태, 진행 상황 표시로 UX 개선

## 향후 확장 계획

1. **실시간 알림**: WebSocket을 통한 크롤링 진행 상황 실시간 업데이트
2. **세션 영속성**: Redis나 데이터베이스를 통한 세션 저장
3. **사용자 인증**: JWT 토큰을 통한 사용자별 검색 이력 관리
4. **검색 결과 캐싱**: 동일한 조건의 검색 결과 캐싱으로 성능 개선
