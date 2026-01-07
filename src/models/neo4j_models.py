"""
Neo4j 결과 검증을 위한 Pydantic 모델
규칙: Every Neo4j response must be parsed/validated via Pydantic models. No raw dict access.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


class Neo4jNode(BaseModel):
    """Neo4j 노드 모델 - 모든 노드 속성을 검증"""
    id: str = Field(..., description="노드 고유 ID")
    labels: List[str] = Field(default_factory=list, description="노드 라벨 리스트")
    name: Optional[str] = Field(None, description="노드 이름")
    type: Optional[str] = Field(None, description="엔티티 타입")
    description: Optional[str] = Field(None, description="노드 설명")
    source: Optional[str] = Field(None, description="데이터 출처")
    
    # 추가 속성들을 동적으로 처리
    model_config = {"extra": "allow"}
    
    @field_validator("labels", mode="before")
    @classmethod
    def validate_labels(cls, v):
        """라벨을 리스트로 변환"""
        if isinstance(v, str):
            return [v]
        if isinstance(v, (set, tuple)):
            return list(v)
        return v or []


class Neo4jRelationship(BaseModel):
    """Neo4j 관계 모델 - 모든 관계 속성을 검증"""
    type: str = Field(..., description="관계 타입")
    source_id: str = Field(..., description="시작 노드 ID")
    target_id: str = Field(..., description="끝 노드 ID")
    weight: Optional[float] = Field(1.0, description="관계 가중치")
    description: Optional[str] = Field(None, description="관계 설명")
    source: Optional[str] = Field(None, description="데이터 출처")
    
    model_config = {"extra": "allow"}


class Neo4jQueryResult(BaseModel):
    """Neo4j 쿼리 결과 모델 - 노드와 관계를 포함"""
    nodes: List[Neo4jNode] = Field(default_factory=list, description="조회된 노드 리스트")
    relationships: List[Neo4jRelationship] = Field(default_factory=list, description="조회된 관계 리스트")
    count: int = Field(0, description="결과 개수")
    
    @classmethod
    def from_neo4j_result(cls, result: List[Dict]) -> "Neo4jQueryResult":
        """
        Neo4j 쿼리 결과를 Pydantic 모델로 변환
        규칙: No raw dict access - 모든 데이터는 모델을 통해 검증
        """
        nodes: List[Neo4jNode] = []
        relationships: List[Neo4jRelationship] = []
        
        for row in result:
            # 노드 추출 (a, b, n 등 다양한 키 지원)
            for key in ["a", "b", "n", "node"]:
                if key in row:
                    node_data = row[key]
                    if hasattr(node_data, "_properties"):
                        props = dict(node_data._properties)
                        props["id"] = str(node_data.id) if hasattr(node_data, "id") else str(node_data)
                        props["labels"] = list(node_data.labels) if hasattr(node_data, "labels") else []
                        nodes.append(Neo4jNode(**props))
            
            # 관계 추출
            for key in ["r", "rel", "relationship"]:
                if key in row:
                    rel_data = row[key]
                    if hasattr(rel_data, "_properties"):
                        props = dict(rel_data._properties)
                        props["type"] = rel_data.type if hasattr(rel_data, "type") else "RELATED"
                        # source와 target 노드 ID 추출
                        if "a" in row and hasattr(row["a"], "id"):
                            props["source_id"] = str(row["a"].id)
                        if "b" in row and hasattr(row["b"], "id"):
                            props["target_id"] = str(row["b"].id)
                        relationships.append(Neo4jRelationship(**props))
        
        return cls(
            nodes=nodes,
            relationships=relationships,
            count=len(nodes) + len(relationships)
        )


class GraphStats(BaseModel):
    """그래프 통계 모델"""
    nodes: int = Field(0, description="노드 개수")
    edges: int = Field(0, description="엣지 개수")
    relationships: int = Field(0, description="관계 개수")
    status: str = Field("success", description="상태")

