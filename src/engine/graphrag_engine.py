"""
GraphRAG 핵심 로직
인덱싱 및 검색 기능을 담당하는 파일이에요!
"""

import os
import asyncio
import sys
from typing import Optional, Literal

from nano_graphrag import GraphRAG
from nano_graphrag.base import QueryParam

# graspologic 패키지가 없을 때를 대비한 더미 모듈
try:
    import graspologic
    import graspologic.utils
except ImportError:
    class DummyGraspologic:
        class partition:
            @staticmethod
            def hierarchical_leiden(*args, **kwargs):
                return {}
        
        class utils:
            @staticmethod
            def largest_connected_component(graph):
                return graph
    
    sys.modules['graspologic'] = DummyGraspologic()
    sys.modules['graspologic.partition'] = DummyGraspologic.partition
    sys.modules['graspologic.utils'] = DummyGraspologic.utils
    print("⚠️  graspologic가 없어서 더미 모듈을 사용해요. 클러스터링 기능이 제한될 수 있어요.")

# src 디렉토리를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    WORKING_DIR,
    DEV_MODE,
    DEV_MODE_MAX_CHARS,
    validate_config,
    NEO4J_AUTO_EXPORT,
)

from utils import (
    openai_model_if,
    openai_embedding_if,
    ollama_model_if,
    ollama_embedding_if,
    preprocess_text,
    chunk_text,
    get_financial_entity_prompt,
)

from engine.planner import QueryPlanner
from models.neo4j_models import GraphStats


class HybridGraphRAGEngine:
    """
    하이브리드 GraphRAG 엔진 클래스
    인덱싱은 OpenAI API를 사용하고, 질문은 API/LOCAL 모드를 선택할 수 있어요!
    """
    
    def __init__(self, working_dir: Optional[str] = None) -> None:
        """
        GraphRAG 엔진 초기화
        
        Args:
            working_dir: 그래프 데이터를 저장할 폴더 경로 (기본값: config.WORKING_DIR)
        """
        validate_config()
        
        self.working_dir = working_dir or WORKING_DIR
        os.makedirs(self.working_dir, exist_ok=True)
        
        # 인덱싱용 GraphRAG 인스턴스 (항상 OpenAI API 사용)
        self.indexing_rag = GraphRAG(
            working_dir=self.working_dir,
            best_model_func=openai_model_if,
            cheap_model_func=openai_model_if,
            embedding_func=openai_embedding_if,
            chunk_token_size=2000,  # 1200 -> 2000 (API 호출 횟수 감소)
            addon_params={
                "entity_extract_max_gleaning": 0,  # 1 -> 0 (재추출 비활성화로 2배 속도 향상)
                "entity_summary_to_max_tokens": 300,  # 요약 길이 제한
            }
        )
        
        # 질문용 GraphRAG 인스턴스들 (API/LOCAL 선택 가능)
        self.query_rag_api = GraphRAG(
            working_dir=self.working_dir,
            best_model_func=openai_model_if,
            cheap_model_func=openai_model_if,
            embedding_func=openai_embedding_if,
        )
        
        self.query_rag_local = GraphRAG(
            working_dir=self.working_dir,
            best_model_func=ollama_model_if,
            cheap_model_func=ollama_model_if,
            embedding_func=openai_embedding_if,  # 인덱싱과 같은 embedding 사용!
        )
        
        print(f"HybridGraphRAGEngine 초기화 완료!")
        print(f"작업 디렉토리: {self.working_dir}")
        print(f"인덱싱 모드: OpenAI API")
        print(f"질문 모드: API 또는 LOCAL 선택 가능")
    
    async def ainsert(self, text: str) -> None:
        """
        비동기로 텍스트를 그래프에 인덱싱하는 함수
        
        Args:
            text: 인덱싱할 텍스트
        """
        # 개발 모드일 때는 텍스트를 짧게 자름
        if DEV_MODE:
            text = text[:DEV_MODE_MAX_CHARS]
            print(f"[DEV_MODE] 텍스트를 {DEV_MODE_MAX_CHARS}자로 제한했어요!")
        
        # 1) 텍스트 전처리
        processed_text = preprocess_text(text)
        
        # 2) 청크 분할
        chunks = chunk_text(processed_text, max_tokens=1200)
        print(f"[DEBUG] 인덱싱용 청크 개수: {len(chunks)}")
        
        # 3) 비동기 병렬 인덱싱 (최대 동시 15개로 증가)
        semaphore = asyncio.Semaphore(15)  # 10 -> 15 (병렬 처리 증가)
        
        async def insert_one(chunk_text: str, idx: int) -> None:
            async with semaphore:
                print(f"[DEBUG] 청크 {idx+1}/{len(chunks)} 인덱싱 시작")
                await self.indexing_rag.ainsert(chunk_text)
                print(f"[DEBUG] 청크 {idx+1}/{len(chunks)} 인덱싱 완료")
        
        # 4) 모든 청크를 동시에 인덱싱
        tasks = [insert_one(chunk, i) for i, chunk in enumerate(chunks)]
        await asyncio.gather(*tasks)
        
        print("인덱싱 완료! (비동기 병렬 처리 + 텍스트 전처리 적용)")
        
        # 5) Neo4j로 자동 업로드 (설정되어 있을 경우)
        if NEO4J_AUTO_EXPORT:
            print("Neo4j로 자동 업로드 시작...")
            try:
                from ..db.neo4j_db import Neo4jDatabase
                graphml_path = os.path.join(self.working_dir, "graph_chunk_entity_relation.graphml")
                
                if os.path.exists(graphml_path):
                    db = Neo4jDatabase()
                    result = await asyncio.to_thread(
                        db.upload_graphml,
                        graphml_path,
                        clear_before=False
                    )
                    if result["status"] == "success":
                        print(f"Neo4j 업로드 완료! 노드: {result['nodes']}개, 관계: {result['edges']}개")
                    else:
                        print(f"Neo4j 업로드 실패: {result['message']}")
                else:
                    print(f"GraphML 파일을 찾을 수 없어요: {graphml_path}")
            except Exception as e:
                print(f"Neo4j 업로드 중 에러 발생: {e}")
                print("NEO4J_URI, NEO4J_PASSWORD가 .env에 설정되어 있는지 확인해주세요!")
        else:
            print("Neo4j 자동 업로드가 비활성화되어 있어요. NEO4J_AUTO_EXPORT=true로 설정하면 자동 업로드됩니다!")
    
    async def aquery(
        self,
        question: str,
        mode: Literal["api", "local"] | None = None,
        auto_plan: bool = True
    ) -> str:
        """
        비동기로 질문에 답변을 찾는 함수
        
        규칙: Planner-Executor 패턴 사용
        - auto_plan=True: Planner가 자동으로 모드 결정
        - auto_plan=False: mode 파라미터 사용
        
        Args:
            question: 질문 내용
            mode: "api" (OpenAI API) 또는 "local" (Ollama) - auto_plan=False일 때만 사용
            auto_plan: Planner를 사용하여 자동으로 모드 결정 (기본값: True)
            
        Returns:
            답변 텍스트
        """
        # Planner를 사용하여 모드 자동 결정
        if auto_plan and mode is None:
            planner = QueryPlanner()
            # 간단한 휴리스틱으로 복잡도 추정 (실제로는 더 정교한 분석 필요)
            mode, complexity, privacy = planner.analyze_query(
                question=question,
                entity_count=1,  # 실제로는 그래프에서 추정
                relationship_depth=2,  # 기본값
                has_pii=False,  # 실제로는 데이터 분석 필요
                needs_synthesis="cross" in question.lower() or "compare" in question.lower()
            )
            print(f"[Planner] 모드: {mode}, 복잡도: {complexity}, 프라이버시: {privacy}")
        
        # mode가 None이면 기본값 local 사용
        if mode is None:
            mode = "local"
        
        print(f"[DEBUG] 질문: {question}")
        print(f"[DEBUG] 모드: {mode}")
        print(f"[DEBUG] 작업 디렉토리: {self.working_dir}")
        
        # 그래프 파일 확인
        graphml_path = os.path.join(self.working_dir, "graph_chunk_entity_relation.graphml")
        if os.path.exists(graphml_path):
            import networkx as nx
            G = nx.read_graphml(graphml_path)
            print(f"[DEBUG] 그래프 노드 수: {G.number_of_nodes()}, 엣지 수: {G.number_of_edges()}")
        else:
            print(f"[DEBUG] 그래프 파일이 없어요: {graphml_path}")
        
        if mode == "api":
            print(f"질문 모드: OpenAI API")
            try:
                # Global 모드: 전체 그래프에서 커뮤니티 리포트 기반 검색 (넓은 범위, revenue 같은 질문에 적합)
                query_param = QueryParam(
                    mode='global',  # local -> global (전체 그래프 검색)
                    top_k=30,  # 20 -> 30 (더 많은 컨텍스트)
                )
                response = await self.query_rag_api.aquery(question, param=query_param)
                print(f"🔍 [DEBUG] query_rag_api.aquery() 완료!")
            except Exception as e:
                print(f"❌ [DEBUG] query_rag_api.aquery() 에러: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                raise
        else:
            print(f"💬 질문 모드: Ollama (로컬)")
            # Ollama 서버 확인
            try:
                import requests
                ollama_check = requests.get("http://localhost:11434/api/tags", timeout=2)
                if ollama_check.status_code != 200:
                    return "❌ Ollama 서버가 실행되지 않았어요! 'ollama serve' 명령어로 서버를 시작해주세요!"
            except:
                return "❌ Ollama 서버에 연결할 수 없어요! 'ollama serve' 명령어로 서버를 시작하거나, 'api' 모드를 사용해주세요!"
            
            try:
                # Global 모드로 검색
                query_param = QueryParam(
                    mode='global',  # 전체 그래프 검색
                    top_k=30,
                )
                response = await self.query_rag_local.aquery(question, param=query_param)
                print(f"🔍 [DEBUG] query_rag_local.aquery() 완료!")
            except Exception as e:
                print(f"❌ [DEBUG] query_rag_local.aquery() 에러: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                raise
        
        # 답변이 비어있거나 "Sorry"로 시작하면 경고
        if not response or response.strip().startswith("Sorry"):
            print("⚠️  그래프에 데이터가 있지만 답변을 생성하지 못했어요.")
            print("💡 더 구체적인 질문을 시도해보세요!")
        
        return response
    
    def get_graph_stats(self) -> GraphStats:
        """
        그래프 통계를 가져오는 함수
        
        Returns:
            그래프 통계 딕셔너리 (nodes, edges, status)
        """
        import networkx as nx
        
        graphml_path = os.path.join(self.working_dir, "graph_chunk_entity_relation.graphml")
        
        if not os.path.exists(graphml_path):
            return GraphStats(nodes=0, edges=0, relationships=0, status="no_file")
        
        G = nx.read_graphml(graphml_path)
        
        return GraphStats(
            nodes=G.number_of_nodes(),
            edges=G.number_of_edges(),
            relationships=G.number_of_edges(),
            status="success"
        )

