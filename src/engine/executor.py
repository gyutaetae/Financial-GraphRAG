"""
Planner-Executor 패턴: Executor 모듈
규칙: Use Cypher queries with Parameterized values and strict LIMIT clauses
"""

import logging
import sys
import os
from typing import Literal, List
from neo4j import GraphDatabase

# src 디렉토리를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.neo4j_models import Neo4jQueryResult, GraphStats
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

logger = logging.getLogger(__name__)


class QueryExecutor:
    """
    Cypher 쿼리를 실행하고 결과를 Pydantic 모델로 반환하는 Executor
    규칙: Parameterized queries + LIMIT clauses + Pydantic validation
    """
    
    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None
    ) -> None:
        """Neo4j 연결 초기화"""
        self.uri = uri or NEO4J_URI
        self.username = username or NEO4J_USERNAME
        self.password = password or NEO4J_PASSWORD
        
        if not all([self.uri, self.username, self.password]):
            raise ValueError("Neo4j 연결 정보가 설정되지 않았어요!")
        
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password)
        )
        logger.info(f"Neo4j 연결 성공: {self.uri.split('@')[-1] if '@' in self.uri else self.uri}")
    
    def execute_query(
        self,
        query: str,
        parameters: dict | None = None,
        limit: int = 50
    ) -> Neo4jQueryResult:
        """
        파라미터화된 Cypher 쿼리 실행
        
        규칙:
        1. Always use parameterized queries
        2. Always include LIMIT clauses
        3. Parse results via Pydantic models
        
        Args:
            query: Cypher 쿼리 (LIMIT 절 포함 권장)
            parameters: 쿼리 파라미터 (SQL injection 방지)
            limit: 기본 LIMIT 값 (쿼리에 LIMIT이 없을 경우)
        """
        # LIMIT 절이 없으면 추가 (메모리 오버플로우 방지)
        if "LIMIT" not in query.upper():
            query = f"{query.rstrip(';')} LIMIT {limit}"
        
        params = parameters or {}
        
        try:
            with self.driver.session() as session:
                result = session.run(query, **params)
                rows = [dict(row) for row in result]
                
                # Pydantic 모델로 검증
                return Neo4jQueryResult.from_neo4j_result(rows)
        except Exception as e:
            logger.error(f"쿼리 실행 실패: {e}")
            raise
    
    def get_graph_stats(self) -> GraphStats:
        """그래프 통계 조회 (Pydantic 모델로 반환)"""
        query = """
        MATCH (n)
        WITH count(n) as node_count
        MATCH ()-[r]->()
        WITH node_count, count(r) as rel_count
        RETURN node_count, rel_count
        LIMIT 1
        """
        
        result = self.execute_query(query, limit=1)
        
        # 통계 추출
        node_count = 0
        rel_count = 0
        
        if result.nodes:
            # 첫 번째 행에서 통계 추출 (실제로는 쿼리 결과에서)
            with self.driver.session() as session:
                stats_result = session.run(query)
                row = stats_result.single()
                if row:
                    node_count = row.get("node_count", 0)
                    rel_count = row.get("rel_count", 0)
        
        return GraphStats(
            nodes=node_count,
            edges=rel_count,
            relationships=rel_count,
            status="success"
        )
    
    def close(self) -> None:
        """연결 종료"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j 연결 종료")

