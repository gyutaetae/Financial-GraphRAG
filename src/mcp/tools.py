"""
MCP Tools - LangChain Tool 래퍼
"""

import json
from typing import Optional, Dict, Any
from .manager import MCPManager


class YahooFinanceTool:
    """
    Yahoo Finance MCP 도구
    
    기능:
    - 실시간 주가 조회
    - 기업 정보 조회
    - 재무 데이터 조회
    """
    
    name = "yahoo_finance"
    description = "실시간 주가, 재무제표, 기업 정보 조회. ticker 심볼을 입력받아 주가 및 기업 정보를 반환합니다."
    
    def __init__(self, mcp_manager: MCPManager):
        """
        Args:
            mcp_manager: MCP Manager 인스턴스
        """
        self.mcp_manager = mcp_manager
    
    async def get_stock_price(self, ticker: str) -> Dict[str, Any]:
        """
        실시간 주가 조회
        
        Args:
            ticker: 주식 심볼 (예: "NVDA", "AAPL")
            
        Returns:
            주가 정보 딕셔너리
        """
        try:
            tool = await self.mcp_manager.get_tool("yahoo-finance", "get_stock_price")
            if tool:
                result = await tool(ticker=ticker)
                return result
            return {"error": "Yahoo Finance 도구를 사용할 수 없습니다"}
        except Exception as e:
            return {"error": f"주가 조회 실패: {str(e)}"}
    
    async def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        기업 정보 조회
        
        Args:
            ticker: 주식 심볼
            
        Returns:
            기업 정보 딕셔너리
        """
        try:
            tool = await self.mcp_manager.get_tool("yahoo-finance", "get_company_info")
            if tool:
                result = await tool(ticker=ticker)
                return result
            return {"error": "Yahoo Finance 도구를 사용할 수 없습니다"}
        except Exception as e:
            return {"error": f"기업 정보 조회 실패: {str(e)}"}
    
    async def get_financial_data(self, ticker: str) -> Dict[str, Any]:
        """
        재무 데이터 조회
        
        Args:
            ticker: 주식 심볼
            
        Returns:
            재무 데이터 딕셔너리
        """
        try:
            tool = await self.mcp_manager.get_tool("yahoo-finance", "get_financial_data")
            if tool:
                result = await tool(ticker=ticker)
                return result
            return {"error": "Yahoo Finance 도구를 사용할 수 없습니다"}
        except Exception as e:
            return {"error": f"재무 데이터 조회 실패: {str(e)}"}
    
    async def run(self, ticker: str, data_type: str = "price") -> str:
        """
        통합 실행 메서드 (LangChain 호환)
        
        Args:
            ticker: 주식 심볼
            data_type: 데이터 타입 ("price", "info", "financial")
            
        Returns:
            JSON 문자열
        """
        if data_type == "price":
            result = await self.get_stock_price(ticker)
        elif data_type == "info":
            result = await self.get_company_info(ticker)
        elif data_type == "financial":
            result = await self.get_financial_data(ticker)
        else:
            result = {"error": f"알 수 없는 데이터 타입: {data_type}"}
        
        return json.dumps(result, ensure_ascii=False)


class TavilySearchTool:
    """
    Tavily Search MCP 도구
    
    기능:
    - 웹 검색 (뉴스, 일반 검색)
    """
    
    name = "tavily_search"
    description = "최신 뉴스 및 웹 검색 (Tavily). 검색어를 입력받아 최신 웹 검색 결과를 반환합니다."
    
    def __init__(self, mcp_manager: MCPManager):
        """
        Args:
            mcp_manager: MCP Manager 인스턴스
        """
        self.mcp_manager = mcp_manager
    
    async def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        웹 검색
        
        Args:
            query: 검색어
            max_results: 최대 결과 수
            
        Returns:
            검색 결과 딕셔너리
        """
        try:
            tool = await self.mcp_manager.get_tool("tavily-search", "tavily_search")
            if tool:
                result = await tool(query=query, max_results=max_results)
                return result
            return {"error": "Tavily Search 도구를 사용할 수 없습니다"}
        except Exception as e:
            return {"error": f"웹 검색 실패: {str(e)}"}
    
    async def run(self, query: str, max_results: int = 5) -> str:
        """
        통합 실행 메서드 (LangChain 호환)
        
        Args:
            query: 검색어
            max_results: 최대 결과 수
            
        Returns:
            JSON 문자열
        """
        result = await self.search(query, max_results)
        return json.dumps(result, ensure_ascii=False)
