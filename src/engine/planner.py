"""
Planner-Executor 패턴: Planner 모듈
규칙: Route to Ollama for PII/internal data; Cloud APIs for cross-entity synthesis
"""

from typing import Literal
from enum import Enum


class QueryComplexity(str, Enum):
    """쿼리 복잡도 레벨"""
    SIMPLE = "simple"  # 단일 엔티티, 1-hop 관계
    MODERATE = "moderate"  # 여러 엔티티, 2-hop 관계
    COMPLEX = "complex"  # 다중 엔티티, 3+ hop, 크로스 도큐먼트


class PrivacyLevel(str, Enum):
    """프라이버시 레벨"""
    PUBLIC = "public"  # 공개 데이터
    INTERNAL = "internal"  # 내부 데이터
    PII = "pii"  # 개인정보 포함


class QueryPlanner:
    """
    쿼리 복잡도와 프라이버시 요구사항에 따라 Local/API 모드를 결정하는 Planner
    규칙: Planner decides whether to use Local (Ollama) or API (GPT-4o/Claude)
    """
    
    @staticmethod
    def analyze_query(
        question: str,
        entity_count: int = 1,
        relationship_depth: int = 1,
        has_pii: bool = False,
        needs_synthesis: bool = False
    ) -> tuple[Literal["local", "api"], QueryComplexity, PrivacyLevel]:
        """
        쿼리를 분석하여 최적의 실행 모드를 결정
        
        Args:
            question: 사용자 질문
            entity_count: 관련 엔티티 개수
            relationship_depth: 관계 탐색 깊이 (hop 수)
            has_pii: 개인정보 포함 여부
            needs_synthesis: 크로스 엔티티 통합 필요 여부
            
        Returns:
            (mode, complexity, privacy_level)
        """
        # 프라이버시 우선 판단
        if has_pii:
            return ("local", QueryComplexity.SIMPLE, PrivacyLevel.PII)
        
        # 복잡도 분석
        if relationship_depth >= 3 or entity_count >= 5 or needs_synthesis:
            complexity = QueryComplexity.COMPLEX
            # 복잡한 통합 작업은 Cloud API 사용
            return ("api", complexity, PrivacyLevel.PUBLIC)
        elif relationship_depth == 2 or entity_count >= 2:
            complexity = QueryComplexity.MODERATE
            # 중간 복잡도는 기본적으로 Local, 필요시 API
            return ("local", complexity, PrivacyLevel.INTERNAL)
        else:
            complexity = QueryComplexity.SIMPLE
            return ("local", complexity, PrivacyLevel.INTERNAL)
    
    @staticmethod
    def should_use_api(
        complexity: QueryComplexity,
        needs_synthesis: bool = False
    ) -> bool:
        """
        Cloud API 사용 여부 결정
        
        규칙:
        - Complex queries → API
        - Cross-entity synthesis → API
        - PII/internal data → Local
        """
        if complexity == QueryComplexity.COMPLEX:
            return True
        if needs_synthesis:
            return True
        return False

