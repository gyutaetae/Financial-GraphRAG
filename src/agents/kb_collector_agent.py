"""
지식 수집 에이전트 (KB Collector Agent)
GraphRAG + Web Search를 통한 정보 수집
"""

import json
from typing import Optional, List, Dict, Any

from .base_agent import BaseAgent
from .agent_context import AgentContext, QueryComplexity


class KBCollectorAgent(BaseAgent):
    """
    지식 수집 에이전트
    
    역할:
    1. Neo4j GraphRAG 검색 (내부 문서 우선)
    2. KV Store fallback (GraphRAG 실패 시)
    3. Web Search (최신 정보 필요 시만)
    """
    
    SYSTEM_PROMPT = """당신은 금융 정보 수집 전문가입니다.

우선순위:
1. Neo4j GraphRAG 검색 (내부 문서 우선)
2. KV Store fallback (GraphRAG 실패 시)
3. Web Search (최신 정보 필요 시만)

반드시 포함:
- 데이터 소스 (파일명, 페이지, URL)
- 신뢰도 점수 (0.0-1.0)
- 상충 데이터 플래그

출력 형식 (JSON):
{
  "sources": [
    {"id": 1, "file": "report.pdf", "page": 5, "excerpt": "...", "confidence": 0.9},
    ...
  ],
  "conflicts": [{"source_ids": [1, 3], "reason": "수치 불일치"}],
  "needs_validation": true/false,
  "summary": "수집된 정보 요약"
}
"""
    
    def __init__(self, engine=None, web_search_enabled: bool = False, mcp_manager=None):
        """
        Args:
            engine: HybridGraphRAGEngine 인스턴스 (None이면 lazy load)
            web_search_enabled: 웹 검색 활성화 여부
            mcp_manager: MCP Manager 인스턴스 (None이면 MCP 도구 비활성화)
        """
        super().__init__(
            name="KB Collector",
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.1  # 정확한 정보 수집을 위해 낮은 온도
        )
        self._engine = engine
        self.web_search_enabled = web_search_enabled
        self._mcp_manager = mcp_manager
        self._yahoo_tool = None
        self._tavily_tool = None
    
    async def execute(self, context: AgentContext) -> AgentContext:
        """
        지식 수집 실행
        
        Args:
            context: 공유 컨텍스트
            
        Returns:
            sources, raw_context가 채워진 컨텍스트
        """
        self._log(f"지식 수집 시작: '{context.question}'")
        context.add_step(f"{self.name}: 지식 수집 시작")
        
        try:
            # 1. GraphRAG 검색 (기존 엔진 활용)
            sources, raw_context, backend = await self._retrieve_from_graphrag(
                context.question
            )
            
            context.sources = sources
            context.raw_context = raw_context
            context.retrieval_backend = backend
            
            # 2. Yahoo Finance로 실시간 데이터 보강 (MCP 활성화 시)
            if self._mcp_manager and self._should_use_yahoo(context.question):
                self._log("Yahoo Finance로 실시간 데이터 보강")
                yahoo_sources = await self._fetch_yahoo_data(context.question)
                if yahoo_sources:
                    context.sources.extend(yahoo_sources)
                    context.retrieval_backend += "+yahoo"
            
            # 3. Tavily Search로 최신 뉴스 보강 (MCP 활성화 시)
            if self._mcp_manager and (context.enable_web_search or len(sources) < 3):
                self._log("Tavily Search로 최신 뉴스 보강")
                tavily_sources = await self._fetch_tavily_search(context.question)
                if tavily_sources:
                    context.sources.extend(tavily_sources)
                    context.retrieval_backend += "+tavily"
            
            # 4. 웹 검색 (기존 방식, MCP 없을 때)
            elif context.enable_web_search and len(sources) < 3:
                self._log("소스가 부족하여 웹 검색 시도")
                web_sources = await self._retrieve_from_web(context.question)
                context.sources.extend(web_sources)
                context.retrieval_backend += "+web"
            
            # 5. 상충 데이터 감지 (LLM 활용)
            if len(context.sources) >= 2:
                conflicts = await self._detect_conflicts(context.sources, context.question)
                context.conflicts = conflicts
            
            self._log(f"수집 완료: {len(context.sources)}개 소스, 백엔드={context.retrieval_backend}")
            context.add_step(f"{self.name}: {len(context.sources)}개 소스 수집 완료")
            
            return context
            
        except Exception as e:
            self._log(f"지식 수집 실패: {e}")
            context.add_step(f"{self.name}: 실패 - {str(e)}")
            # 빈 결과라도 다음 에이전트로 전달
            return context
    
    async def _retrieve_from_graphrag(
        self,
        question: str
    ) -> tuple[List[Dict], str, str]:
        """
        GraphRAG 엔진에서 정보 검색
        
        Returns:
            (sources, raw_context, backend)
        """
        # Lazy load engine
        if self._engine is None:
            from engine import HybridGraphRAGEngine
            self._engine = HybridGraphRAGEngine()
        
        try:
            # return_context=True로 호출하여 sources 받기
            result = await self._engine.aquery(
                question=question,
                mode="api",  # 메모리 효율을 위해 API 모드
                return_context=True,
                top_k=30
            )
            
            if isinstance(result, dict):
                sources = result.get("sources", [])
                # raw_context는 sources의 excerpt를 결합
                raw_context = "\n\n".join([
                    f"[{s.get('id', i+1)}] {s.get('file', 'Unknown')}: {s.get('excerpt', '')}"
                    for i, s in enumerate(sources)
                ])
                backend = result.get("retrieval_backend", "graphrag")
                return sources, raw_context, backend
            else:
                # 단순 문자열 응답인 경우
                return [], str(result), "graphrag"
                
        except Exception as e:
            self._log(f"GraphRAG 검색 실패: {e}")
            return [], "", "error"
    
    async def _retrieve_from_web(self, question: str) -> List[Dict]:
        """
        웹 검색으로 추가 정보 수집
        
        Returns:
            웹 소스 리스트
        """
        try:
            from search import web_search
            from config import WEB_SEARCH_MAX_RESULTS
            
            results = await web_search(question, max_results=WEB_SEARCH_MAX_RESULTS or 5)
            
            web_sources = []
            for i, result in enumerate(results):
                web_sources.append({
                    "id": f"web_{i+1}",
                    "file": result.get("title", "Web Source"),
                    "page": "N/A",
                    "excerpt": result.get("snippet", ""),
                    "url": result.get("url", ""),
                    "confidence": 0.7  # 웹 소스는 낮은 신뢰도
                })
            
            return web_sources
            
        except Exception as e:
            self._log(f"웹 검색 실패: {e}")
            return []
    
    async def _detect_conflicts(
        self,
        sources: List[Dict],
        question: str
    ) -> List[Dict]:
        """
        소스 간 상충 데이터 감지 (LLM 활용)
        
        Returns:
            상충 정보 리스트
        """
        try:
            # 소스 요약 생성
            sources_summary = "\n".join([
                f"Source {s.get('id', i+1)}: {s.get('excerpt', '')[:200]}"
                for i, s in enumerate(sources[:5])  # 최대 5개만 비교
            ])
            
            prompt = f"""질문: {question}

다음 소스들을 분석하여 수치나 사실이 상충하는 부분을 찾아주세요:

{sources_summary}

상충이 있다면 JSON 형식으로 반환:
{{"conflicts": [{{"source_ids": [1, 2], "reason": "매출 수치 불일치"}}]}}

상충이 없다면:
{{"conflicts": []}}
"""
            
            response = await self._call_llm(prompt, temperature=0.0, max_tokens=500)
            
            # JSON 파싱
            try:
                result = json.loads(response)
                return result.get("conflicts", [])
            except json.JSONDecodeError:
                self._log("상충 감지 응답 파싱 실패")
                return []
                
        except Exception as e:
            self._log(f"상충 감지 실패: {e}")
            return []
    
    def _should_use_yahoo(self, question: str) -> bool:
        """
        질문이 Yahoo Finance 데이터가 필요한지 판단
        
        Args:
            question: 사용자 질문
            
        Returns:
            Yahoo Finance 사용 여부
        """
        # 주가, 시가총액, 재무제표 등 실시간 데이터 키워드
        keywords = [
            "주가", "stock price", "현재가", "시가총액", "market cap",
            "재무제표", "financial", "매출", "revenue", "이익", "profit",
            "eps", "pe ratio", "배당", "dividend"
        ]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in keywords)
    
    async def _extract_ticker(self, question: str) -> Optional[str]:
        """
        질문에서 주식 티커 추출 (LLM 활용)
        
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
    
    async def _fetch_yahoo_data(self, question: str) -> List[Dict]:
        """
        Yahoo Finance로 실시간 데이터 수집
        
        Args:
            question: 사용자 질문
            
        Returns:
            Yahoo Finance 소스 리스트
        """
        try:
            # Yahoo Tool 초기화 (lazy)
            if not self._yahoo_tool:
                from mcp.tools import YahooFinanceTool
                self._yahoo_tool = YahooFinanceTool(self._mcp_manager)
            
            # 티커 추출
            ticker = await self._extract_ticker(question)
            if not ticker:
                self._log("티커를 추출할 수 없어 Yahoo Finance 스킵")
                return []
            
            self._log(f"Yahoo Finance 조회: {ticker}")
            
            # 주가 정보 조회
            price_data = await self._yahoo_tool.get_stock_price(ticker)
            
            # 소스 형식으로 변환
            yahoo_sources = []
            if "error" not in price_data:
                excerpt = f"{ticker} 실시간 주가: ${price_data.get('price', 'N/A')}"
                if "change_percent" in price_data:
                    excerpt += f" ({price_data['change_percent']:+.2f}%)"
                
                yahoo_sources.append({
                    "id": f"yahoo_{ticker}",
                    "file": f"Yahoo Finance - {ticker}",
                    "page": "실시간",
                    "excerpt": excerpt,
                    "url": f"https://finance.yahoo.com/quote/{ticker}",
                    "confidence": 0.95,  # 실시간 데이터는 높은 신뢰도
                    "data": price_data
                })
            
            return yahoo_sources
            
        except Exception as e:
            self._log(f"Yahoo Finance 조회 실패: {e}")
            return []
    
    async def _fetch_tavily_search(self, question: str) -> List[Dict]:
        """
        Tavily Search로 최신 뉴스 수집
        
        Args:
            question: 사용자 질문
            
        Returns:
            Tavily Search 소스 리스트
        """
        try:
            # Tavily Tool 초기화 (lazy)
            if not self._tavily_tool:
                from mcp.tools import TavilySearchTool
                self._tavily_tool = TavilySearchTool(self._mcp_manager)
            
            self._log(f"Tavily Search 조회: {question}")
            
            # 웹 검색 실행
            search_result = await self._tavily_tool.search(question, max_results=5)
            
            # 소스 형식으로 변환
            tavily_sources = []
            if "error" not in search_result:
                results = search_result.get("results", [])
                for i, result in enumerate(results):
                    tavily_sources.append({
                        "id": f"tavily_{i+1}",
                        "file": result.get("title", "Tavily Search Result"),
                        "page": "웹",
                        "excerpt": result.get("content", result.get("snippet", "")),
                        "url": result.get("url", ""),
                        "confidence": 0.80,  # Tavily는 높은 신뢰도
                        "score": result.get("score", 0.0)
                    })
            
            return tavily_sources
            
        except Exception as e:
            self._log(f"Tavily Search 실패: {e}")
            return []
