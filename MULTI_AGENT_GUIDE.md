# Multi-Agent 시스템 가이드

## 개요

8GB RAM 환경에 최적화된 4개 에이전트 협업 시스템입니다.

## 아키텍처

```
User Question
    ↓
Master Agent (오케스트레이터)
    ↓
KB Collector Agent (정보 수집)
    ↓
Analyst Agent (검증 및 분석)
    ↓
Writer Agent (리포트 작성)
    ↓
Final Report
```

## 에이전트 역할

### 1. Master Agent
- 질문 복잡도 분석 (SIMPLE/MODERATE/COMPLEX)
- 워커 에이전트 선택 및 실행
- 결과 취합

### 2. KB Collector Agent
- Neo4j GraphRAG 검색 (우선)
- KV Store fallback
- Web Search (선택적)
- 소스 간 상충 감지

### 3. Analyst Agent
- 수치 정확성 검증
- 논리적 일관성 확인
- 인과관계 분석
- 신뢰도 점수화

### 4. Writer Agent
- 투자자용 전문 리포트 작성
- 투자 제언 (BUY/HOLD/SELL)
- 모든 주장에 인용 포함

## 사용 방법

### API 사용

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "NVIDIA 주식 살까요?",
    "use_multi_agent": true,
    "enable_web_search": false
  }'
```

### Streamlit UI 사용

1. Streamlit 앱 실행
2. "Multi-Agent Analysis Mode" 체크박스 활성화
3. 질문 입력
4. 결과 확인:
   - 최종 리포트
   - 투자 제언 (BUY/HOLD/SELL)
   - 핵심 인사이트
   - 처리 단계
   - 출처

## 복잡도별 파이프라인

### SIMPLE (단순 팩트 검색)
- 예: "NVIDIA 매출은?"
- 파이프라인: KB Collector만

### MODERATE (수치 분석)
- 예: "NVIDIA YoY 성장률은?"
- 파이프라인: KB Collector → Analyst

### COMPLEX (투자 조언)
- 예: "NVIDIA 주식 살까요?"
- 파이프라인: KB Collector → Analyst → Writer

## 메모리 최적화

### 8GB RAM 대응 전략

1. **OpenAI API 우선 사용**
   - 로컬 LLM(Ollama) 대신 API 사용
   - 메모리 부담 최소화

2. **Lazy Loading**
   - 에이전트는 필요할 때만 초기화
   - 싱글톤 패턴 적용

3. **메모리 모니터링**
   - 85% 임계값 설정
   - 초과 시 MemoryError 발생

4. **캐싱 활용**
   - Neo4jRetriever 캐시 (60초 TTL)
   - LLM 응답 캐시

### 메모리 사용률 확인

```bash
curl http://localhost:8000/memory
```

응답 예시:
```json
{
  "total_gb": 8.0,
  "used_gb": 2.8,
  "available_gb": 5.2,
  "percent": 35.0,
  "status": "healthy",
  "message": "메모리 사용률이 정상입니다."
}
```

## 예상 메모리 사용량

- Base System: ~1.5GB
- FastAPI + Streamlit: ~500MB
- Neo4j Driver: ~200MB
- OpenAI API Client: ~100MB
- Agent Context: ~500MB
- **총 예상**: ~2.8GB (8GB 대비 35%)

## 테스트 시나리오

### 1. 단순 질문
```json
{
  "question": "NVIDIA 매출은?",
  "use_multi_agent": true
}
```
예상: KB Collector만 실행

### 2. 수치 분석
```json
{
  "question": "NVIDIA YoY 성장률은?",
  "use_multi_agent": true
}
```
예상: KB Collector + Analyst 실행

### 3. 투자 조언
```json
{
  "question": "NVIDIA 주식 살까요?",
  "use_multi_agent": true
}
```
예상: 전체 파이프라인 실행, BUY/HOLD/SELL 제언 포함

## 응답 형식

```json
{
  "question": "NVIDIA 주식 살까요?",
  "answer": "## 요약\n...\n\n## 상세 분석\n...",
  "sources": [...],
  "confidence": 0.85,
  "recommendation": "BUY",
  "insights": [
    "매출 YoY +62% 증가는 데이터센터 부문 성장 기인",
    "..."
  ],
  "retrieval_backend": "kv_fallback",
  "processing_steps": [
    "Master: 오케스트레이션 시작",
    "KB Collector: 9개 소스 수집 완료",
    "Analyst: 5개 주장 검증 완료 (신뢰도 85%)",
    "Writer: 리포트 작성 완료 (추천: BUY)"
  ],
  "mode": "MULTI_AGENT",
  "status": "success"
}
```

## 문제 해결

### 메모리 부족
```
MemoryError: Analyst: 메모리 사용률 87.3% 초과 (임계값: 85%)
```
**해결**: 다른 프로그램 종료 또는 임계값 조정

### LLM 호출 실패
```
RuntimeError: KB Collector: LLM 호출 최대 재시도 초과
```
**해결**: OpenAI API 키 확인 또는 네트워크 상태 확인

### Neo4j 연결 실패
```
ValueError: Neo4j 연결 정보가 설정되지 않았어요!
```
**해결**: KV Store fallback 자동 실행, Neo4j 설정 확인

## 확장 가능성

### 새 에이전트 추가

```python
from agents.base_agent import BaseAgent
from agents.agent_context import AgentContext

class RiskAssessorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Risk Assessor",
            system_prompt="당신은 리스크 평가 전문가입니다...",
            temperature=0.2
        )
    
    async def execute(self, context: AgentContext) -> AgentContext:
        # 리스크 평가 로직
        context.risk_score = 0.3
        return context
```

### Master Agent에 통합

```python
# master_agent.py
self._risk_assessor = RiskAssessorAgent()

# execute_pipeline에서 호출
if context.complexity == QueryComplexity.COMPLEX:
    context = await self._risk_assessor.execute(context)
```

## 참고 자료

- [ROUTER_IMPLEMENTATION.md](ROUTER_IMPLEMENTATION.md) - 쿼리 라우팅 로직
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - 배포 가이드
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Docker 설정
