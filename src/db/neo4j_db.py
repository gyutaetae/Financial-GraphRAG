"""
Neo4j 데이터베이스 연동 모듈
GraphRAG 인덱싱 결과를 Neo4j에 저장하고, PDF 파싱 기능도 제공해요!
"""

import os
import sys
from typing import Dict, Optional
import networkx as nx

# .env 파일 읽기
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# neo4j 드라이버가 있는지 확인
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("⚠️  neo4j 패키지가 설치되지 않았어요. 'pip install neo4j'로 설치해주세요.")

# src 디렉토리를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from utils import extract_text_from_pdf


class Neo4jDatabase:
    """
    Neo4j 데이터베이스에 연결하고 GraphRAG 데이터를 저장하는 클래스예요!
    
    이 클래스는:
    1. Neo4j/AuraDB에 연결해요
    2. GraphRAG의 노드(Entities)를 Neo4j 노드로 변환해요
    3. GraphRAG의 엣지(Relationships)를 Neo4j 관계로 변환해요
    4. MERGE 쿼리로 중복 없이 저장해요
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> None:
        """
        Neo4j 연결을 초기화하는 함수
        
        Args:
            uri: Neo4j URI (예: neo4j+s://xxxxx.databases.neo4j.io)
            username: Neo4j 사용자 이름 (기본값: config에서 가져옴)
            password: Neo4j 비밀번호 (기본값: config에서 가져옴)
        """
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j 패키지가 설치되지 않았어요! 'pip install neo4j'로 설치해주세요.")
        
        # 환경변수 또는 config에서 연결 정보 가져오기
        self.uri = uri or NEO4J_URI or os.getenv("NEO4J_URI", "")
        self.username = username or NEO4J_USERNAME or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or NEO4J_PASSWORD or os.getenv("NEO4J_PASSWORD", "")
        
        # 연결 정보 검증
        if not self.uri:
            raise ValueError("NEO4J_URI가 설정되지 않았어요! .env 파일에 추가해주세요.")
        if not self.password:
            raise ValueError("NEO4J_PASSWORD가 설정되지 않았어요! .env 파일에 추가해주세요.")
        
        # AuraDB URI 형식 확인
        valid_protocols = ("neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://")
        if not any(self.uri.startswith(proto) for proto in valid_protocols):
            raise ValueError(
                f"⚠️  NEO4J_URI 형식이 올바르지 않아요!\n"
                f"💡 AuraDB는 neo4j+s:// 또는 neo4j+ssc:// 형식을 사용해요!\n"
                f"   현재 URI: {self.uri}"
            )
        
        # Neo4j 드라이버 생성
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        
        print(f"✅ Neo4j 연결 성공! URI: {self.uri.split('@')[-1] if '@' in self.uri else self.uri}")
    
    def close(self):
        """연결을 닫는 함수예요!"""
        if self.driver:
            self.driver.close()
            print("🔌 Neo4j 연결이 종료되었어요.")
    
    def create_node(self, node_id: str, node_data: Dict[str, str | float | int]) -> None:
        """
        Neo4j에 노드를 생성하는 함수예요!
        
        Args:
            node_id: 노드 ID (고유 식별자)
            node_data: 노드 속성 딕셔너리
        """
        # 규칙: Parameterized queries로 SQL injection 방지
        query = """
        MERGE (n:Entity {id: $node_id})
        SET n.name = $name,
            n.type = $type,
            n.description = $description,
            n.source = $source
        """
        
        # 노드 데이터에서 속성 추출 (타입 안전성 보장)
        params: Dict[str, str] = {
            "node_id": str(node_id),
            "name": str(node_data.get("entity_name", node_id)),
            "type": str(node_data.get("entity_type", "UNKNOWN")),
            "description": str(node_data.get("description", "")),
            "source": str(node_data.get("source_id", ""))
        }
        
        # 쿼리 실행
        with self.driver.session() as session:
            session.run(query, **params)
    
    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_data: Dict[str, str | float | int]
    ) -> None:
        """
        Neo4j에 관계를 생성하는 함수예요!
        
        Args:
            source_id: 시작 노드 ID
            target_id: 끝 노드 ID
            rel_data: 관계 속성 딕셔너리
        """
        # 관계 타입 (기본값: RELATED) - 파라미터화 불가능하므로 검증 필요
        rel_type_raw = str(rel_data.get("type", "RELATED"))
        # 보안: 관계 타입에 특수문자 제거 (SQL injection 방지)
        rel_type = "".join(c for c in rel_type_raw.upper().replace(" ", "_") if c.isalnum() or c == "_")
        if not rel_type:
            rel_type = "RELATED"
        
        # 규칙: Parameterized queries 사용 (관계 타입은 동적이지만 검증됨)
        query = f"""
        MATCH (a:Entity {{id: $source_id}})
        MATCH (b:Entity {{id: $target_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r.weight = $weight,
            r.description = $description,
            r.source = $source
        """
        
        # 타입 안전성 보장
        weight = rel_data.get("weight", 1.0)
        if not isinstance(weight, (int, float)):
            weight = 1.0
        
        params: Dict[str, str | float] = {
            "source_id": str(source_id),
            "target_id": str(target_id),
            "weight": float(weight),
            "description": str(rel_data.get("description", "")),
            "source": str(rel_data.get("source_id", ""))
        }
        
        # 쿼리 실행
        with self.driver.session() as session:
            session.run(query, **params)
    
    def upload_graphml(
        self,
        graphml_path: str,
        clear_before: bool = False
    ) -> Dict[str, str | int]:
        """
        GraphML 파일을 읽어서 Neo4j에 업로드하는 함수
        
        Args:
            graphml_path: GraphML 파일 경로
            clear_before: True면 기존 데이터를 먼저 삭제
            
        Returns:
            업로드 결과 딕셔너리 (status, message, nodes, edges)
        """
        if not os.path.exists(graphml_path):
            return {
                "status": "error",
                "message": f"GraphML 파일을 찾을 수 없어요: {graphml_path}",
                "nodes": 0,
                "edges": 0
            }
        
        try:
            # 기존 데이터 삭제 (옵션)
            if clear_before:
                print("🗑️ 기존 Neo4j 데이터를 삭제합니다...")
                self.clear_all()
            
            print(f"📊 GraphML 파일 로딩 중: {graphml_path}")
            
            # NetworkX로 GraphML 파일 읽기
            G = nx.read_graphml(graphml_path)
            
            print(f"🔍 그래프 통계: 노드 {G.number_of_nodes()}개, 엣지 {G.number_of_edges()}개")
            
            # 1) 모든 노드를 Neo4j에 생성
            print("📝 노드 업로드 중...")
            node_count = 0
            for node_id, node_data in G.nodes(data=True):
                self.create_node(node_id, node_data)
                node_count += 1
                if node_count % 100 == 0:
                    print(f"   진행: {node_count}/{G.number_of_nodes()} 노드")
            
            print(f"✅ {node_count}개 노드 업로드 완료!")
            
            # 2) 모든 엣지를 Neo4j에 생성
            print("🔗 관계 업로드 중...")
            edge_count = 0
            for source, target, edge_data in G.edges(data=True):
                self.create_relationship(source, target, edge_data)
                edge_count += 1
                if edge_count % 100 == 0:
                    print(f"   진행: {edge_count}/{G.number_of_edges()} 관계")
            
            print(f"✅ {edge_count}개 관계 업로드 완료!")
            
            return {
                "status": "success",
                "message": "Neo4j 업로드 완료!",
                "nodes": node_count,
                "edges": edge_count
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Neo4j 업로드 중 에러: {str(e)}",
                "nodes": 0,
                "edges": 0
            }
    
    def clear_all(self) -> None:
        """Neo4j의 모든 데이터를 삭제하는 함수예요! (주의: 위험한 작업)"""
        query = "MATCH (n) DETACH DELETE n"
        
        with self.driver.session() as session:
            session.run(query)
        
        print("🗑️ Neo4j의 모든 데이터가 삭제되었어요!")
    
    def get_stats(self) -> Dict[str, int]:
        """Neo4j의 통계를 가져오는 함수예요!"""
        with self.driver.session() as session:
            # 노드 수 조회
            node_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_result.single()["count"]
            
            # 관계 수 조회
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.single()["count"]
        
        return {"nodes": node_count, "relationships": rel_count}


    def parse_pdf_to_text(self, pdf_path: str) -> str:
        """
        PDF 파일에서 텍스트를 추출하는 함수
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            추출된 텍스트
        """
        return extract_text_from_pdf(pdf_path)


# 하위 호환성을 위한 별칭
Neo4jDriver = Neo4jDatabase


# 헬퍼 함수 (하위 호환성 유지)
def export_to_neo4j(graphml_path: str, clear_before: bool = False) -> Dict[str, Any]:
    """
    GraphML 파일을 Neo4j에 업로드하는 헬퍼 함수 (하위 호환성)
    
    Args:
        graphml_path: GraphML 파일 경로
        clear_before: True면 기존 데이터를 먼저 삭제
        
    Returns:
        업로드 결과 딕셔너리
    """
    try:
        db = Neo4jDatabase()
        result = db.upload_graphml(graphml_path, clear_before=clear_before)
        db.close()
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Neo4j 업로드 중 에러: {str(e)}"
        }


# 테스트용 코드
if __name__ == "__main__":
    # GraphML 파일 경로
    graphml_file = "/tmp/graph_storage_hybrid/graph_chunk_entity_relation.graphml"
    
    if os.path.exists(graphml_file):
        print(f"📊 GraphML 파일 발견: {graphml_file}")
        result = export_to_neo4j(graphml_file, clear_before=False)
        print(f"🎉 결과: {result}")
    else:
        print(f"❌ GraphML 파일을 찾을 수 없어요: {graphml_file}")
        print("💡 먼저 GraphRAG 인덱싱을 실행해주세요!")

