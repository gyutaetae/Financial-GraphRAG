"""
작성 에이전트 (Writer Agent)
투자자용 최종 리포트 작성
"""

import json
from typing import Optional

from .base_agent import BaseAgent
from .agent_context import AgentContext


class WriterAgent(BaseAgent):
    """
    작성 에이전트
    
    역할:
    1. 검증된 데이터를 바탕으로 투자 리포트 작성
    2. 전문 금융 용어 사용
    3. 모든 주장에 인용 포함
    4. 투자 제언 제공 (BUY/HOLD/SELL)
    """
    
    SYSTEM_PROMPT = """당신은 투자 전략가 및 전문 작가입니다.

리포트 구조:
1. 요약 (3-5줄)
2. 상세 분석 (데이터 기반)
3. 투자 리스크 (정량화)
4. 최종 제언 (BUY/HOLD/SELL)

작성 규칙:
- 모든 주장에 [Source N] 인용 포함
- 전문 금융 용어 사용 (현금 흐름, 리스크 헤지 등)
- 평문 출력 (HTML 금지)
- 수치는 소수점 2자리까지
- 객관적이고 균형 잡힌 시각

출력 형식 (JSON):
{
  "report": "## 요약\n...\n\n## 상세 분석\n...\n\n## 투자 리스크\n...\n\n## 최종 제언\n...",
  "recommendation": "BUY/HOLD/SELL",
  "confidence": 0.85
}
"""
    
    def __init__(self, neo4j_db=None):
        """
        Args:
            neo4j_db: Neo4jDatabase 인스턴스 (Shared Memory용)
        """
        super().__init__(
            name="Writer",
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.3  # 약간의 창의성 허용
        )
        self._neo4j_db = neo4j_db
    
    async def execute(self, context: AgentContext) -> AgentContext:
        """
        리포트 작성 실행
        
        Args:
            context: Analyst가 채운 validated_data를 포함한 컨텍스트
            
        Returns:
            final_report, recommendation이 채워진 컨텍스트
        """
        self._log("리포트 작성 시작")
        context.add_step(f"{self.name}: 리포트 작성 시작")
        
        if not context.validated_data and not context.sources:
            self._log("검증된 데이터가 없어 작성 스킵")
            context.final_report = "분석할 데이터가 부족합니다."
            context.add_step(f"{self.name}: 데이터 부족, 스킵")
            return context
        
        try:
            # 1. Neo4j에서 전체 컨텍스트 읽기 (LangGraph 워크플로우)
            full_context = context
            if self._neo4j_db and context.neo4j_keys:
                full_context = await self._load_full_context(context)
                self._log(f"Neo4j에서 전체 컨텍스트 로드 완료")
            
            # 2. 추론 경로 생성 (서브태스크 기반)
            if context.subtasks:
                context.reasoning_path = self._build_reasoning_path(context)
            
            # 3. LLM을 활용한 리포트 작성
            report_result = await self._generate_report(
                context.question,
                context.validated_data,
                context.insights,
                context.sources,
                context.reasoning_path
            )
            
            # 2. 결과를 컨텍스트에 반영
            context.final_report = report_result.get("report", "리포트 생성 실패")
            context.recommendation = report_result.get("recommendation", None)
            
            # confidence는 Analyst의 것과 Writer의 것을 평균
            writer_confidence = report_result.get("confidence", 0.5)
            context.confidence = (context.confidence + writer_confidence) / 2
            
            self._log(f"리포트 작성 완료 (추천: {context.recommendation}, 신뢰도: {context.confidence:.2f})")
            context.add_step(
                f"{self.name}: 리포트 작성 완료 "
                f"(추천: {context.recommendation or 'N/A'}, 신뢰도 {context.confidence:.0%})"
            )
            
            return context
            
        except Exception as e:
            self._log(f"리포트 작성 실패: {e}")
            context.add_step(f"{self.name}: 실패 - {str(e)}")
            # 실패 시 폴백: validated_data를 텍스트로 변환
            context.final_report = self._create_fallback_report(context)
            return context
    
    async def _generate_report(
        self,
        question: str,
        validated_data: list,
        insights: list,
        sources: list,
        reasoning_path: list = None
    ) -> dict:
        """
        LLM을 활용한 리포트 생성
        
        Args:
            reasoning_path: 추론 경로 (옵션)
        
        Returns:
            {"report": str, "recommendation": str, "confidence": float}
        """
        # 검증된 데이터 요약
        validated_summary = "\n".join([
            f"- {item.get('claim', '')} (신뢰도: {item.get('confidence', 0):.2f}, 출처: {item.get('citations', [])})"
            for item in validated_data[:10]
        ])
        
        # 인사이트 요약
        insights_summary = "\n".join([f"- {insight}" for insight in insights[:5]])
        
        # 소스 목록
        sources_list = "\n".join([
            f"[{s.get('id', i+1)}] {s.get('file', 'Unknown')} (Page {s.get('page', 'N/A')})"
            for i, s in enumerate(sources[:10])
        ])
        
        # 추론 경로 (있는 경우)
        reasoning_section = ""
        if reasoning_path:
            reasoning_section = f"\n\n추론 경로:\n" + "\n".join([
                f"{i+1}. {step}" for i, step in enumerate(reasoning_path)
            ])
        
        prompt = f"""질문: {question}

검증된 데이터:
{validated_summary}

핵심 인사이트:
{insights_summary}

출처:
{sources_list}{reasoning_section}

위 정보를 바탕으로 투자자용 전문 리포트를 작성하세요.

요구사항:
1. 구조: 요약 → 상세 분석 → 투자 리스크 → 최종 제언
2. 모든 주장에 [N] 형태로 출처 인용
3. 전문 금융 용어 사용
4. 평문 출력 (HTML 금지)
5. 투자 제언: BUY/HOLD/SELL 중 하나

JSON 형식으로 응답:
{{
  "report": "## 요약\\n...\\n\\n## 상세 분석\\n...\\n\\n## 투자 리스크\\n...\\n\\n## 최종 제언\\n...",
  "recommendation": "BUY/HOLD/SELL",
  "confidence": 0.85
}}
"""
        
        try:
            response = await self._call_llm(prompt, temperature=0.3, max_tokens=2500)
            
            # JSON 파싱
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                self._log("LLM 응답 JSON 파싱 실패, 텍스트 그대로 사용")
                return {
                    "report": response,
                    "recommendation": None,
                    "confidence": 0.5
                }
                
        except Exception as e:
            self._log(f"LLM 리포트 생성 실패: {e}")
            raise
    
    def _create_fallback_report(self, context: AgentContext) -> str:
        """
        LLM 실패 시 폴백 리포트 생성
        """
        lines = [f"질문: {context.question}", ""]
        
        if context.validated_data:
            lines.append("## 검증된 정보")
            for item in context.validated_data[:5]:
                claim = item.get("claim", "")
                citations = item.get("citations", [])
                citation_str = ", ".join([f"[{c}]" for c in citations])
                lines.append(f"- {claim} {citation_str}")
            lines.append("")
        
        if context.insights:
            lines.append("## 핵심 인사이트")
            for insight in context.insights[:3]:
                lines.append(f"- {insight}")
            lines.append("")
        
        if context.sources:
            lines.append("## 출처")
            for i, source in enumerate(context.sources[:5]):
                lines.append(
                    f"[{source.get('id', i+1)}] {source.get('file', 'Unknown')} "
                    f"(Page {source.get('page', 'N/A')})"
                )
        
        return "\n".join(lines)
    
    async def _load_full_context(self, context: AgentContext) -> AgentContext:
        """
        Neo4j에서 전체 컨텍스트 로드 (모든 서브태스크 데이터 통합)
        
        Args:
            context: 공유 컨텍스트
            
        Returns:
            통합 컨텍스트
        """
        try:
            import json
            
            all_sources = []
            all_insights = []
            
            for key in context.neo4j_keys:
                # Neo4j에서 노드 조회
                with self._neo4j_db.driver.session() as session:
                    result = session.run(
                        "MATCH (n {id: $key}) RETURN n",
                        key=key
                    )
                    
                    for record in result:
                        node = record["n"]
                        data_str = node.get("data", "{}")
                        data = json.loads(data_str)
                        
                        # 소스 통합
                        sources = data.get("sources", [])
                        all_sources.extend(sources)
                        
                        # 서브태스크 정보 추출
                        if "subtask" in data:
                            subtask = data["subtask"]
                            all_insights.append(
                                f"서브태스크 {subtask['id']} ({subtask['task']}): "
                                f"{len(sources)}개 소스 수집"
                            )
            
            # 중복 제거
            seen_ids = set()
            unique_sources = []
            for s in all_sources:
                sid = s.get("id", s.get("excerpt", "")[:50])
                if sid not in seen_ids:
                    seen_ids.add(sid)
                    unique_sources.append(s)
            
            # 컨텍스트 업데이트
            if unique_sources:
                context.sources = unique_sources
            if all_insights:
                context.insights.extend(all_insights)
            
            return context
            
        except Exception as e:
            self._log(f"Neo4j 컨텍스트 로드 실패: {e}")
            return context
    
    def _build_reasoning_path(self, context: AgentContext) -> list:
        """
        서브태스크 기반 추론 경로 생성
        
        Args:
            context: 공유 컨텍스트
            
        Returns:
            추론 경로 문자열 리스트
        """
        path = []
        
        if not context.subtasks:
            return path
        
        path.append(f"질문 분해: {len(context.subtasks)}개 서브태스크")
        
        for subtask in context.subtasks:
            subtask_id = subtask["id"]
            task_desc = subtask.get("task", "")
            target = subtask.get("target", "general")
            
            # 해당 서브태스크의 소스 개수
            subtask_sources = [
                s for s in context.sources 
                if s.get("subtask_id") == subtask_id
            ]
            
            path.append(
                f"서브태스크 {subtask_id} ({target}): {task_desc} "
                f"→ {len(subtask_sources)}개 소스 수집"
            )
        
        # 검증 단계
        if context.validated_data:
            path.append(
                f"데이터 검증: {len(context.validated_data)}개 주장 검증 완료 "
                f"(신뢰도 {context.confidence:.0%})"
            )
        
        # 반복 횟수
        if context.iteration_count > 0:
            path.append(f"피드백 루프: {context.iteration_count}회 정보 보강")
        
        return path
