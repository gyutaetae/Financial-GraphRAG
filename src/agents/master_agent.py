"""
마스터 에이전트 (Master Agent)
워커 에이전트들을 오케스트레이션하는 지휘관
"""

from typing import Optional

from .base_agent import BaseAgent
from .agent_context import AgentContext, QueryComplexity
from .kb_collector_agent import KBCollectorAgent
from .analyst_agent import AnalystAgent
from .writer_agent import WriterAgent


class MasterAgent(BaseAgent):
    """
    마스터 에이전트
    
    역할:
    1. 질문 복잡도 분석
    2. 필요한 워커 에이전트 결정
    3. 워커 에이전트 순차 실행
    4. 최종 결과 취합
    """
    
    SYSTEM_PROMPT = """당신은 금융 분석 팀의 수석 오케스트레이터입니다.
사용자의 질문을 분석하여 복잡도를 판단하고, 적절한 워커 에이전트를 호출합니다.

복잡도 판단 기준:
- SIMPLE: 단순 팩트 검색 (예: "NVIDIA 매출은?")
- MODERATE: 수치 분석 필요 (예: "NVIDIA YoY 성장률은?")
- COMPLEX: 투자 조언 등 종합 분석 (예: "NVIDIA 주식 살까요?")

워커 에이전트 호출 규칙:
- SIMPLE: KB Collector만
- MODERATE: KB Collector + Analyst
- COMPLEX: KB Collector + Analyst + Writer

JSON 형식으로 응답:
{
  "complexity": "simple/moderate/complex",
  "reasoning": "판단 근거"
}
"""
    
    def __init__(self, engine=None, mcp_manager=None):
        """
        Args:
            engine: HybridGraphRAGEngine 인스턴스 (워커들에게 전달)
            mcp_manager: MCP Manager 인스턴스 (워커들에게 전달)
        """
        super().__init__(
            name="Master",
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.1
        )
        self._engine = engine
        self._mcp_manager = mcp_manager
        
        # 워커 에이전트들 (Lazy initialization)
        self._kb_collector: Optional[KBCollectorAgent] = None
        self._analyst: Optional[AnalystAgent] = None
        self._writer: Optional[WriterAgent] = None
    
    async def execute(self, context: AgentContext) -> AgentContext:
        """
        마스터 에이전트 실행
        
        Args:
            context: 공유 컨텍스트
            
        Returns:
            최종 결과가 담긴 컨텍스트
        """
        self._log(f"질문 분석 시작: '{context.question}'")
        context.add_step(f"{self.name}: 오케스트레이션 시작")
        
        try:
            # 1. 복잡도 분석 (이미 설정되어 있지 않은 경우)
            if context.complexity == QueryComplexity.SIMPLE:
                complexity = await self._analyze_complexity(context.question)
                context.complexity = complexity
                self._log(f"복잡도 분석 결과: {complexity.value}")
            
            # 2. 워커 에이전트 초기화
            self._initialize_workers(context.enable_web_search)
            
            # 3. 워커 에이전트 순차 실행
            context = await self._execute_pipeline(context)
            
            self._log("오케스트레이션 완료")
            context.add_step(f"{self.name}: 오케스트레이션 완료")
            
            return context
            
        except Exception as e:
            self._log(f"오케스트레이션 실패: {e}")
            context.add_step(f"{self.name}: 실패 - {str(e)}")
            # 에러 메시지를 final_report에 담아 반환
            context.final_report = f"처리 중 오류가 발생했습니다: {str(e)}"
            context.confidence = 0.0
            return context
    
    async def _analyze_complexity(self, question: str) -> QueryComplexity:
        """
        질문 복잡도 분석 (LLM 활용)
        
        Returns:
            QueryComplexity enum
        """
        try:
            prompt = f"""다음 질문의 복잡도를 분석하세요:

질문: {question}

JSON 형식으로 응답:
{{"complexity": "simple/moderate/complex", "reasoning": "판단 근거"}}
"""
            
            response = await self._call_llm(prompt, temperature=0.0, max_tokens=200)
            
            # JSON 파싱
            import json
            try:
                result = json.loads(response)
                complexity_str = result.get("complexity", "simple").lower()
                
                if "complex" in complexity_str:
                    return QueryComplexity.COMPLEX
                elif "moderate" in complexity_str:
                    return QueryComplexity.MODERATE
                else:
                    return QueryComplexity.SIMPLE
                    
            except json.JSONDecodeError:
                self._log("복잡도 분석 응답 파싱 실패, SIMPLE로 기본 설정")
                return QueryComplexity.SIMPLE
                
        except Exception as e:
            self._log(f"복잡도 분석 실패: {e}, SIMPLE로 기본 설정")
            return QueryComplexity.SIMPLE
    
    def _initialize_workers(self, web_search_enabled: bool) -> None:
        """워커 에이전트 초기화 (Lazy)"""
        if self._kb_collector is None:
            self._kb_collector = KBCollectorAgent(
                engine=self._engine,
                web_search_enabled=web_search_enabled,
                mcp_manager=self._mcp_manager
            )
        
        if self._analyst is None:
            self._analyst = AnalystAgent(mcp_manager=self._mcp_manager)
        
        if self._writer is None:
            self._writer = WriterAgent()
    
    async def _execute_pipeline(self, context: AgentContext) -> AgentContext:
        """
        복잡도에 따라 워커 에이전트 파이프라인 실행
        
        Args:
            context: 공유 컨텍스트
            
        Returns:
            업데이트된 컨텍스트
        """
        # 1. KB Collector는 항상 실행
        context = await self._kb_collector.execute(context)
        
        # 소스가 없으면 조기 종료
        if not context.sources:
            context.final_report = "해당 문서들에서는 관련 정보를 찾을 수 없습니다."
            context.confidence = 0.0
            return context
        
        # 2. MODERATE 이상: Analyst 실행
        if context.complexity in [QueryComplexity.MODERATE, QueryComplexity.COMPLEX]:
            context = await self._analyst.execute(context)
        
        # 3. COMPLEX: Writer 실행
        if context.complexity == QueryComplexity.COMPLEX:
            context = await self._writer.execute(context)
        else:
            # SIMPLE/MODERATE는 Analyst 결과를 그대로 사용
            if context.validated_data:
                # validated_data를 텍스트로 변환
                report_lines = []
                for item in context.validated_data:
                    claim = item.get("claim", "")
                    citations = item.get("citations", [])
                    citation_str = ", ".join([f"[{c}]" for c in citations])
                    report_lines.append(f"{claim} {citation_str}")
                
                context.final_report = "\n\n".join(report_lines)
            else:
                # raw_context를 그대로 사용
                context.final_report = context.raw_context or "정보를 찾을 수 없습니다."
        
        return context
