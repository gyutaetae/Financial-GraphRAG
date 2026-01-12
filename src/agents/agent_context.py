"""
에이전트 간 데이터 전달을 위한 공유 컨텍스트
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class QueryComplexity(str, Enum):
    """쿼리 복잡도"""
    SIMPLE = "simple"       # 단순 팩트 검색
    MODERATE = "moderate"   # 수치 분석 필요
    COMPLEX = "complex"     # 투자 조언 등 종합 분석


@dataclass
class AgentContext:
    """
    에이전트 간 공유 컨텍스트
    각 에이전트는 이 컨텍스트를 받아서 작업하고, 결과를 추가하여 반환
    """
    # 입력
    question: str
    complexity: QueryComplexity = QueryComplexity.SIMPLE
    enable_web_search: bool = False
    
    # Planner 결과 (LangGraph 워크플로우용)
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    iteration_count: int = 0  # Feedback Loop 제어
    neo4j_keys: List[str] = field(default_factory=list)  # Neo4j 저장 키 추적
    needs_more_info: bool = False  # Analyst의 충분성 판단
    
    # KB Collector 결과
    sources: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    raw_context: str = ""
    
    # Analyst 결과
    validated_data: List[Dict[str, Any]] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    removed_claims: List[str] = field(default_factory=list)
    
    # Writer 결과
    final_report: str = ""
    recommendation: Optional[str] = None  # BUY/HOLD/SELL
    reasoning_path: List[str] = field(default_factory=list)  # 추론 경로
    
    # 메타데이터
    retrieval_backend: str = ""
    confidence: float = 0.0
    processing_steps: List[str] = field(default_factory=list)
    
    def add_step(self, step: str) -> None:
        """처리 단계 추가 (디버깅용)"""
        self.processing_steps.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """API 응답용 딕셔너리로 변환"""
        return {
            "answer": self.final_report,
            "sources": self.sources,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "insights": self.insights,
            "retrieval_backend": self.retrieval_backend,
            "processing_steps": self.processing_steps,
            "reasoning_path": self.reasoning_path,
            "mode": "AGENTIC_WORKFLOW" if self.subtasks else "MULTI_AGENT"
        }
