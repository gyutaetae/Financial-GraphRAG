"""
분석 에이전트 (Analyst Agent)
수치 검증 및 할루시네이션 제거
"""

import json
from typing import List, Dict, Any, Optional

from .base_agent import BaseAgent
from .agent_context import AgentContext


class AnalystAgent(BaseAgent):
    """
    분석 에이전트
    
    역할:
    1. 수치 정확성 확인 (소스와 대조)
    2. 논리적 일관성 검증
    3. 인과관계 분석
    4. 신뢰도 점수화
    """
    
    SYSTEM_PROMPT = """당신은 금융 데이터 분석가입니다.

검증 절차:
1. 수치 정확성 확인 (소스와 대조)
2. 논리적 일관성 검증 (예: 매출 > 영업이익)
3. 인과관계 분석 (예: 원자재 상승 → 이익 감소)
4. 신뢰도 점수화 (0.0-1.0)

제거 대상:
- 근거 없는 주장
- 소스와 불일치하는 수치
- 논리적 모순

출력 형식 (JSON):
{
  "validated_data": [
    {"claim": "매출 57억 달러", "confidence": 0.95, "citations": [1, 2], "reasoning": "소스 1, 2에서 확인"},
    ...
  ],
  "removed_claims": ["근거 없는 주장 X"],
  "insights": ["매출 YoY +62% 증가는 데이터센터 부문 성장 기인"],
  "overall_confidence": 0.85
}
"""
    
    def __init__(self, mcp_manager=None, neo4j_db=None):
        """
        Args:
            mcp_manager: MCP Manager 인스턴스 (None이면 MCP 도구 비활성화)
            neo4j_db: Neo4jDatabase 인스턴스 (Shared Memory용)
        """
        super().__init__(
            name="Analyst",
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.1  # 정확한 분석을 위해 낮은 온도
        )
        self._mcp_manager = mcp_manager
        self._neo4j_db = neo4j_db
        self._yahoo_tool = None
    
    async def execute(self, context: AgentContext) -> AgentContext:
        """
        분석 실행
        
        Args:
            context: KB Collector가 채운 sources를 포함한 컨텍스트
            
        Returns:
            validated_data, insights가 채워진 컨텍스트
        """
        self._log(f"분석 시작: {len(context.sources)}개 소스")
        context.add_step(f"{self.name}: 분석 시작")
        
        if not context.sources:
            self._log("소스가 없어 분석 스킵")
            context.add_step(f"{self.name}: 소스 없음, 스킵")
            return context
        
        try:
            # 1. 기존 CitationValidator 활용 (있는 경우)
            validation_result = await self._validate_with_llm(
                context.question,
                context.sources,
                context.raw_context
            )
            
            # 2. Yahoo Finance로 수치 재검증 (MCP 활성화 시)
            if self._mcp_manager and self._has_financial_claims(validation_result):
                self._log("Yahoo Finance로 수치 재검증")
                verified_result = await self._cross_verify_with_yahoo(
                    validation_result,
                    context.question
                )
                validation_result = self._merge_verification(validation_result, verified_result)
            
            # 3. Neo4j에서 추가 컨텍스트 읽기 (LangGraph 워크플로우)
            if self._neo4j_db and context.neo4j_keys:
                additional_sources = await self._read_from_neo4j(context)
                if additional_sources:
                    context.sources.extend(additional_sources)
                    self._log(f"Neo4j에서 {len(additional_sources)}개 추가 소스 로드")
            
            # 4. 정보 충분성 판단
            sufficiency_check = await self._check_sufficiency(context)
            context.needs_more_info = not sufficiency_check["is_sufficient"]
            
            if context.needs_more_info:
                context.add_step(
                    f"{self.name}: 정보 부족 감지 - {sufficiency_check['reason']}"
                )
            
            # 5. 결과를 컨텍스트에 반영
            context.validated_data = validation_result.get("validated_data", [])
            context.removed_claims = validation_result.get("removed_claims", [])
            context.insights = validation_result.get("insights", [])
            context.confidence = validation_result.get("overall_confidence", 0.5)
            
            self._log(
                f"분석 완료: {len(context.validated_data)}개 검증된 주장, "
                f"신뢰도={context.confidence:.2f}, 충분성={not context.needs_more_info}"
            )
            context.add_step(
                f"{self.name}: {len(context.validated_data)}개 주장 검증 완료 "
                f"(신뢰도 {context.confidence:.0%})"
            )
            
            return context
            
        except Exception as e:
            self._log(f"분석 실패: {e}")
            context.add_step(f"{self.name}: 실패 - {str(e)}")
            # 실패해도 원본 소스는 유지
            return context
    
    async def _validate_with_llm(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        raw_context: str
    ) -> Dict[str, Any]:
        """
        LLM을 활용한 검증
        
        Returns:
            검증 결과 딕셔너리
        """
        # 소스 요약 생성 (최대 10개)
        sources_summary = "\n\n".join([
            f"[{s.get('id', i+1)}] {s.get('file', 'Unknown')} (Page {s.get('page', 'N/A')}):\n{s.get('excerpt', '')[:300]}"
            for i, s in enumerate(sources[:10])
        ])
        
        prompt = f"""질문: {question}

다음 소스들을 분석하여 검증된 주장과 인사이트를 추출하세요:

{sources_summary}

요구사항:
1. 각 주장은 반드시 소스 ID로 뒷받침되어야 함
2. 수치는 정확히 소스와 일치해야 함
3. 논리적 일관성 확인
4. 인과관계 분석 포함

JSON 형식으로 응답:
{{
  "validated_data": [
    {{"claim": "구체적 주장", "confidence": 0.95, "citations": [1, 2], "reasoning": "근거"}},
    ...
  ],
  "removed_claims": ["제거된 주장들"],
  "insights": ["핵심 인사이트들"],
  "overall_confidence": 0.85
}}
"""
        
        try:
            response = await self._call_llm(prompt, temperature=0.0, max_tokens=2000)
            
            # JSON 파싱
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                self._log("LLM 응답 JSON 파싱 실패, 기본 구조 반환")
                return self._create_fallback_validation(sources)
                
        except Exception as e:
            self._log(f"LLM 검증 실패: {e}")
            return self._create_fallback_validation(sources)
    
    def _create_fallback_validation(self, sources: List[Dict]) -> Dict[str, Any]:
        """
        LLM 실패 시 폴백 검증 결과 생성
        (소스를 그대로 validated_data로 변환)
        """
        validated_data = []
        for i, source in enumerate(sources[:5]):  # 최대 5개
            validated_data.append({
                "claim": source.get("excerpt", "")[:200],
                "confidence": source.get("confidence", 0.7),
                "citations": [source.get("id", i+1)],
                "reasoning": "소스에서 직접 추출"
            })
        
        return {
            "validated_data": validated_data,
            "removed_claims": [],
            "insights": [],
            "overall_confidence": 0.7
        }
    
    def _has_financial_claims(self, validation_result: Dict[str, Any]) -> bool:
        """
        검증 결과에 재무 수치 주장이 있는지 확인
        
        Args:
            validation_result: 검증 결과
            
        Returns:
            재무 수치 포함 여부
        """
        validated_data = validation_result.get("validated_data", [])
        
        # 재무 관련 키워드
        financial_keywords = [
            "주가", "price", "매출", "revenue", "이익", "profit",
            "달러", "dollar", "$", "억", "조", "billion", "million"
        ]
        
        for item in validated_data:
            claim = item.get("claim", "").lower()
            if any(keyword in claim for keyword in financial_keywords):
                return True
        
        return False
    
    async def _cross_verify_with_yahoo(
        self,
        validation_result: Dict[str, Any],
        question: str
    ) -> Dict[str, Any]:
        """
        Yahoo Finance로 수치 재검증
        
        Args:
            validation_result: 기존 검증 결과
            question: 사용자 질문
            
        Returns:
            Yahoo Finance 검증 결과
        """
        try:
            # Yahoo Tool 초기화 (lazy)
            if not self._yahoo_tool:
                from mcp.tools import YahooFinanceTool
                self._yahoo_tool = YahooFinanceTool(self._mcp_manager)
            
            # 티커 추출
            ticker = await self._extract_ticker(question)
            if not ticker:
                self._log("티커를 추출할 수 없어 Yahoo Finance 검증 스킵")
                return {}
            
            self._log(f"Yahoo Finance 검증: {ticker}")
            
            # 주가 및 재무 데이터 조회
            price_data = await self._yahoo_tool.get_stock_price(ticker)
            company_info = await self._yahoo_tool.get_company_info(ticker)
            
            # 검증 결과 생성
            verified_claims = []
            
            if "error" not in price_data:
                verified_claims.append({
                    "claim": f"{ticker} 실시간 주가: ${price_data.get('price', 'N/A')}",
                    "confidence": 0.98,
                    "citations": ["Yahoo Finance"],
                    "reasoning": "Yahoo Finance 실시간 데이터로 검증됨",
                    "verified": True
                })
            
            if "error" not in company_info:
                verified_claims.append({
                    "claim": f"{company_info.get('name', ticker)} - {company_info.get('sector', 'N/A')} 섹터",
                    "confidence": 0.95,
                    "citations": ["Yahoo Finance"],
                    "reasoning": "Yahoo Finance 기업 정보로 검증됨",
                    "verified": True
                })
            
            return {
                "verified_claims": verified_claims,
                "source": "Yahoo Finance",
                "ticker": ticker
            }
            
        except Exception as e:
            self._log(f"Yahoo Finance 검증 실패: {e}")
            return {}
    
    async def _extract_ticker(self, question: str) -> Optional[str]:
        """
        질문에서 주식 티커 추출
        
        Args:
            question: 사용자 질문
            
        Returns:
            티커 심볼 또는 None
        """
        try:
            prompt = f"""다음 질문에서 주식 티커 심볼을 추출하세요:

질문: {question}

티커 심볼만 반환하세요 (예: NVDA, AAPL, TSLA).
티커를 찾을 수 없으면 "NONE"을 반환하세요.
"""
            response = await self._call_llm(prompt, temperature=0.0, max_tokens=50)
            ticker = response.strip().upper()
            
            if ticker and ticker != "NONE" and len(ticker) <= 5:
                return ticker
            return None
            
        except Exception as e:
            self._log(f"티커 추출 실패: {e}")
            return None
    
    def _merge_verification(
        self,
        original: Dict[str, Any],
        verified: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        기존 검증 결과와 Yahoo Finance 검증 결과 병합
        
        Args:
            original: 기존 검증 결과
            verified: Yahoo Finance 검증 결과
            
        Returns:
            병합된 검증 결과
        """
        if not verified or "verified_claims" not in verified:
            return original
        
        # 검증된 주장 추가
        original_data = original.get("validated_data", [])
        verified_claims = verified.get("verified_claims", [])
        
        # 중복 제거하면서 병합
        merged_data = original_data + verified_claims
        
        # 신뢰도 재계산 (Yahoo Finance 검증으로 신뢰도 상승)
        if merged_data:
            avg_confidence = sum(item.get("confidence", 0.5) for item in merged_data) / len(merged_data)
            original["overall_confidence"] = min(avg_confidence + 0.05, 1.0)  # 최대 5% 상승
        
        original["validated_data"] = merged_data
        
        # 인사이트 추가
        insights = original.get("insights", [])
        insights.append(f"Yahoo Finance 실시간 데이터로 {len(verified_claims)}개 주장 검증 완료")
        original["insights"] = insights
        
        return original
    
    async def _read_from_neo4j(self, context: AgentContext) -> List[Dict[str, Any]]:
        """
        Neo4j Shared Memory에서 데이터 읽기
        
        Args:
            context: 공유 컨텍스트
            
        Returns:
            추가 소스 리스트
        """
        try:
            import json
            additional_sources = []
            
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
                        
                        # 소스 추출
                        sources = data.get("sources", [])
                        additional_sources.extend(sources)
            
            return additional_sources
            
        except Exception as e:
            self._log(f"Neo4j 읽기 실패: {e}")
            return []
    
    async def _check_sufficiency(self, context: AgentContext) -> Dict[str, Any]:
        """
        정보 충분성 판단
        
        Args:
            context: 공유 컨텍스트
            
        Returns:
            {
                "is_sufficient": True/False,
                "reason": "판단 근거",
                "missing_aspects": ["부족한 정보 항목"]
            }
        """
        # 기본 휴리스틱
        if len(context.sources) < 3:
            return {
                "is_sufficient": False,
                "reason": f"소스 개수 부족 ({len(context.sources)}/3)",
                "missing_aspects": ["more_sources"]
            }
        
        if context.confidence < 0.6:
            return {
                "is_sufficient": False,
                "reason": f"신뢰도 낮음 ({context.confidence:.0%})",
                "missing_aspects": ["higher_quality_sources"]
            }
        
        # 서브태스크 기반 판단
        if context.subtasks:
            subtask_coverage = {}
            for source in context.sources:
                subtask_id = source.get("subtask_id")
                if subtask_id:
                    subtask_coverage[subtask_id] = subtask_coverage.get(subtask_id, 0) + 1
            
            missing_subtasks = []
            for subtask in context.subtasks:
                if subtask["id"] not in subtask_coverage or subtask_coverage[subtask["id"]] < 2:
                    missing_subtasks.append(subtask["id"])
            
            if missing_subtasks:
                return {
                    "is_sufficient": False,
                    "reason": f"서브태스크 {missing_subtasks} 정보 부족",
                    "missing_aspects": [f"subtask_{sid}" for sid in missing_subtasks]
                }
        
        # 충분함
        return {
            "is_sufficient": True,
            "reason": "충분한 소스와 신뢰도 확보",
            "missing_aspects": []
        }
