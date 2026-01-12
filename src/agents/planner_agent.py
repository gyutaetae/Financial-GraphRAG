"""
Planner Agent - 질문 분해 및 서브태스크 생성
"""

import json
from typing import List, Dict
from .base_agent import BaseAgent
from .agent_context import AgentContext


class PlannerAgent(BaseAgent):
    """
    플래너 에이전트
    
    역할:
    1. 복잡한 질문을 최소 3단계 서브태스크로 분해
    2. 각 서브태스크의 target 카테고리 지정
    3. 정보 수집 우선순위 설정
    
    예시:
    질문: "트럼프 당선이 강남 부동산에 미치는 영향은?"
    
    서브태스크:
    1. 트럼프 정책 파악 (target: policy)
    2. 금리 전이 경로 분석 (target: economy)
    3. 부동산 상관관계 확인 (target: realestate)
    """
    
    SYSTEM_PROMPT = """당신은 복잡한 금융 질문을 체계적으로 분해하는 전략 플래너입니다.

**목표**: 사용자의 질문을 논리적으로 연결된 3-5개의 서브태스크로 분해하여, 
각 태스크가 최종 답변을 위한 필수 정보를 수집하도록 설계합니다.

**서브태스크 설계 원칙**:
1. **인과관계 추적**: 원인 → 중간 과정 → 결과 순서로 분해
2. **정보 계층화**: 글로벌 → 지역, 거시 → 미시 순으로 범위 좁히기
3. **검증 가능성**: 각 태스크는 데이터로 검증 가능해야 함
4. **최소 3개, 최대 5개**: 너무 적으면 피상적, 너무 많으면 메모리 부족

**Target 카테고리**:
- policy: 정책, 법률, 규제
- economy: 경제지표, 금리, 환율
- market: 시장 동향, 가격 변동
- realestate: 부동산 시장
- stock: 주식, 기업 실적
- geopolitics: 지정학적 이벤트
- correlation: 자산 간 상관관계

**출력 형식 (JSON)**:
{
  "subtasks": [
    {
      "id": 1,
      "task": "구체적인 태스크 설명",
      "target": "카테고리",
      "priority": 1,
      "reasoning": "왜 이 태스크가 필요한지"
    },
    ...
  ],
  "overall_strategy": "전체 분석 전략 요약"
}

**중요**: 반드시 유효한 JSON 형식으로만 응답하세요. 추가 설명은 넣지 마세요."""

    def __init__(self):
        super().__init__(
            name="Planner",
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.3  # 약간의 창의성 허용
        )
    
    async def execute(self, context: AgentContext) -> AgentContext:
        """
        질문을 분석하고 서브태스크 생성
        
        Args:
            context: 공유 컨텍스트 (question 필드 필수)
            
        Returns:
            subtasks가 추가된 컨텍스트
        """
        self._log(f"질문 분석 시작: {context.question}")
        context.add_step(f"[Planner] 질문 분해 시작")
        
        # 질문 복잡도에 따라 프롬프트 조정
        complexity_hint = {
            "simple": "이 질문은 단순하므로 3개 서브태스크로 충분합니다.",
            "moderate": "이 질문은 중간 복잡도이므로 3-4개 서브태스크가 필요합니다.",
            "complex": "이 질문은 복잡하므로 4-5개 서브태스크로 철저히 분해하세요."
        }
        
        hint = complexity_hint.get(context.complexity.value, complexity_hint["moderate"])
        
        prompt = f"""{hint}

**사용자 질문**: {context.question}

위 질문을 분석하여 서브태스크로 분해하세요. JSON 형식으로만 응답하세요."""
        
        # LLM 호출
        try:
            response = await self._call_llm(prompt, max_tokens=1500)
            
            # JSON 파싱
            subtasks_data = self._parse_json_response(response)
            
            if not subtasks_data or "subtasks" not in subtasks_data:
                raise ValueError("Invalid response format: 'subtasks' key missing")
            
            context.subtasks = subtasks_data["subtasks"]
            
            self._log(f"서브태스크 {len(context.subtasks)}개 생성 완료")
            context.add_step(f"[Planner] {len(context.subtasks)}개 서브태스크 생성 완료")
            
            # 전략 로깅
            if "overall_strategy" in subtasks_data:
                context.add_step(f"[Planner] 전략: {subtasks_data['overall_strategy']}")
            
            return context
            
        except Exception as e:
            self._log(f"서브태스크 생성 실패: {e}")
            
            # Fallback: 기본 서브태스크 생성
            context.subtasks = self._create_fallback_subtasks(context.question)
            context.add_step(f"[Planner] Fallback: 기본 {len(context.subtasks)}개 서브태스크 사용")
            
            return context
    
    def _parse_json_response(self, response: str) -> Dict:
        """
        LLM 응답에서 JSON 추출 및 파싱
        
        Args:
            response: LLM 응답 텍스트
            
        Returns:
            파싱된 딕셔너리
        """
        # 코드 블록 제거
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        # JSON 파싱
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            self._log(f"JSON 파싱 실패: {e}")
            raise
    
    def _create_fallback_subtasks(self, question: str) -> List[Dict]:
        """
        LLM 실패 시 기본 서브태스크 생성
        
        Args:
            question: 사용자 질문
            
        Returns:
            기본 서브태스크 리스트
        """
        return [
            {
                "id": 1,
                "task": f"'{question}'와 관련된 최근 이벤트 및 정책 조사",
                "target": "policy",
                "priority": 1,
                "reasoning": "배경 컨텍스트 파악"
            },
            {
                "id": 2,
                "task": f"'{question}'의 핵심 경제 지표 및 데이터 수집",
                "target": "economy",
                "priority": 2,
                "reasoning": "정량적 근거 확보"
            },
            {
                "id": 3,
                "task": f"'{question}'에 대한 전문가 의견 및 분석 리포트 탐색",
                "target": "market",
                "priority": 3,
                "reasoning": "다각적 관점 확보"
            }
        ]
