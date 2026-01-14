"""
GraphRAG 핵심 로직 - Privacy Mode 전용
직접 구현한 Ollama → JSON → Cypher → Neo4j 파이프라인 사용
nano-graphrag 의존성 완전 제거
"""

import os
import asyncio
import sys
from typing import Optional, Literal, Dict, List

# src 디렉토리를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    WORKING_DIR,
    DEV_MODE,
    DEV_MODE_MAX_CHARS,
    validate_config,
    NEO4J_AUTO_EXPORT,
    ENABLE_DOMAIN_SCHEMA,
    PRIVACY_MODE,
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
)

from utils import (
    preprocess_text,
    chunk_text,
    get_financial_entity_prompt,
)

from engine.planner import QueryPlanner
from models.neo4j_models import GraphStats
from engine.neo4j_retriever import Neo4jRetriever
from engine.entity_classifier import EntityClassifier
from engine.relationship_inferencer import RelationshipInferencer
from db.neo4j_db import Neo4jDatabase


class PrivacyGraphRAGEngine:
    """
    Privacy-First GraphRAG 엔진 (nano-graphrag 제거)
    직접 구현: Ollama → JSON → Cypher → Neo4j
    8GB RAM 최적화, 로컬 전용 처리
    """
    
    def __init__(self, working_dir: Optional[str] = None) -> None:
        """
        GraphRAG 엔진 초기화 (Privacy Mode 전용)
        
        Args:
            working_dir: 그래프 데이터를 저장할 폴더 경로 (기본값: config.WORKING_DIR)
        
        Raises:
            RuntimeError: Privacy Mode 설정이 불완전한 경우
        """
        validate_config()
        
        self.working_dir = working_dir or WORKING_DIR
        os.makedirs(self.working_dir, exist_ok=True)
        
        # Privacy Mode 필수 확인
        if not PRIVACY_MODE and not (NEO4J_URI and NEO4J_PASSWORD):
            raise RuntimeError(
                "Privacy Mode requires PRIVACY_MODE=true OR valid Neo4j config. "
                "Check .env file: PRIVACY_MODE, NEO4J_URI, NEO4J_PASSWORD"
            )
        
        print("🔧 Privacy Mode: 직접 구현 Graph Builder (Ollama → JSON → Cypher → Neo4j)")
        
        # Import Privacy components (필수)
        try:
            from engine.privacy_ingestor import PrivacyIngestor
            from engine.privacy_graph_builder import PrivacyGraphBuilder
            
            self.privacy_ingestor = PrivacyIngestor()
            self.privacy_graph_builder = None  # Lazy init (Neo4j 필요 시)
            self.use_privacy_mode = True
            print("✅ Privacy Graph Builder 준비 완료")
        except Exception as e:
            print(f"❌ Privacy Graph Builder 초기화 실패: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Privacy Mode initialization failed: {e}")

        # Neo4j 기반 정밀 Retriever (근거/출처 생성용)
        self._neo4j_retriever: Neo4jRetriever | None = None
        
        # 도메인 스키마 관련 컴포넌트 (lazy loading)
        self._entity_classifier: EntityClassifier | None = None
        self._relationship_inferencer: RelationshipInferencer | None = None
        self._neo4j_db: Neo4jDatabase | None = None
        self.enable_domain_schema = ENABLE_DOMAIN_SCHEMA
        
        print(f"✅ PrivacyGraphRAGEngine 초기화 완료!")
        print(f"📁 작업 디렉토리: {self.working_dir}")
        print(f"🔧 인덱싱 모드: Privacy Graph Builder (직접 구현)")
        print(f"🏗️  도메인 스키마: {'활성화' if self.enable_domain_schema else '비활성화'}")
    
    def _get_neo4j_db(self):
        """
        Lazy initialization of Neo4j database connection
        
        Returns:
            Neo4jDatabase instance
        """
        if self._neo4j_db is None:
            from db.neo4j_db import Neo4jDatabase
            self._neo4j_db = Neo4jDatabase(
                uri=NEO4J_URI,
                username=NEO4J_USERNAME,
                password=NEO4J_PASSWORD
            )
            print(f"✅ Neo4j DB 연결 초기화: {NEO4J_URI}")
        return self._neo4j_db
    
    async def ainsert(self, text: str) -> None:
        """
        비동기로 텍스트를 그래프에 인덱싱하는 함수
        Privacy Graph Builder 우선 사용, nano-graphrag는 fallback
        
        Args:
            text: 인덱싱할 텍스트
        """
        # 개발 모드일 때는 텍스트를 짧게 자름
        if DEV_MODE:
            text = text[:DEV_MODE_MAX_CHARS]
            print(f"[DEV_MODE] 텍스트를 {DEV_MODE_MAX_CHARS}자로 제한했어요!")
        
        # Privacy Graph Builder 사용 (우선)
        if self.use_privacy_mode and self.privacy_ingestor:
            print("🔧 Privacy Graph Builder로 인덱싱 (직접 구현: LLM → JSON → Cypher → Neo4j)")
            
            # Initialize Neo4j if needed
            if self._neo4j_db is None:
                self._neo4j_db = self._get_neo4j_db()
            
            # Initialize Privacy Graph Builder
            if self.privacy_graph_builder is None:
                from engine.privacy_graph_builder import PrivacyGraphBuilder
                self.privacy_graph_builder = PrivacyGraphBuilder(neo4j_db=self._neo4j_db)
            
            # Save text to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(text)
                temp_path = f.name
            
            try:
                # Ingest and build graph
                chunks = self.privacy_ingestor.ingest_file(temp_path)
                stats = await self.privacy_graph_builder.build_graph_sequential(chunks)
                
                print(f"✅ Privacy Graph Builder 인덱싱 완료!")
                print(f"   📊 Entities: {stats['entities_extracted']}")
                print(f"   🔗 Relationships: {stats['relationships_extracted']}")
                print(f"   💾 Queries: {stats['queries_executed']}")
                
                # Cleanup
                import os
                os.unlink(temp_path)
                
                # 도메인 노드 변환은 이미 Privacy Graph Builder에서 처리됨
                return
                
            except Exception as e:
                print(f"❌ Privacy Graph Builder 실패: {e}")
                import traceback
                traceback.print_exc()
                
                # Cleanup temp file
                import os
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                
                raise RuntimeError(f"Indexing failed: {e}")
    
    async def aquery(
        self,
        question: str,
        mode: Literal["api", "local"] | None = None,
        auto_plan: bool = True,
        return_context: bool = False,
        top_k: int = 30
    ) -> str | dict:
        """
        비동기로 질문에 답변을 찾는 함수
        
        규칙: Planner-Executor 패턴 사용
        - auto_plan=True: Planner가 자동으로 모드 결정
        - auto_plan=False: mode 파라미터 사용
        
        Args:
            question: 질문 내용
            mode: "api" (OpenAI API) 또는 "local" (Ollama) - auto_plan=False일 때만 사용
            auto_plan: Planner를 사용하여 자동으로 모드 결정 (기본값: True)
            return_context: True일 경우 답변과 함께 출처 정보 반환 (기본값: False)
            top_k: 검색할 텍스트 청크 개수 (기본값: 30)
            
        Returns:
            return_context=False: 답변 텍스트 (str)
            return_context=True: {"answer": str, "sources": List[dict]} (dict)
        """
        # #region agent log
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(__import__('json').dumps({"location":"graphrag_engine.py:171","message":"aquery() entry","data":{"question":question,"mode":mode,"return_context":return_context,"top_k":top_k},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+'\n')
        # #endregion
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
        
        # Privacy Mode: Use Privacy Analyst Agent (Neo4j + Ollama)
        if self.use_privacy_mode:
            print("🔧 Privacy Mode: Privacy Analyst Agent 사용 (Neo4j + Ollama)")
            
            try:
                from agents.privacy_analyst import PrivacyAnalystAgent
                
                # Initialize agent
                analyst = PrivacyAnalystAgent()
                
                # Get answer
                response = await analyst.analyze(question)
                
                print(f"✅ Privacy Analyst Agent 답변 완료!")
                
                # Return with context if requested
                if return_context:
                    # Get context from Neo4j
                    ctx = await self._aretrieve_context_from_neo4j(question=question, top_sources=min(top_k, 10))
                    return {
                        "answer": response,
                        "sources": ctx.get("sources", []),
                        "retrieval_backend": "privacy_mode_neo4j"
                    }
                
                return response
                
            except Exception as e:
                print(f"❌ Privacy Analyst Agent 실패: {e}")
                import traceback
                traceback.print_exc()
                
                # Privacy Mode가 실패한 경우 상세한 에러 메시지 제공
                error_msg = f"""
Privacy Mode 실행 실패: {str(e)}

해결 방법:
1. Ollama 서버 실행 확인: ollama serve
2. Neo4j 연결 확인: docker ps | grep neo4j
3. 모델 다운로드: ollama pull qwen2.5-coder:3b
4. .env 설정 확인:
   - NEO4J_URI=bolt://localhost:7687
   - NEO4J_PASSWORD=password
   - PRIVACY_MODE=true

Streamlit UI에서 "Privacy Mode" 체크박스를 활성화했는지 확인하세요.
"""
                raise RuntimeError(error_msg)
        
        # Privacy Mode is mandatory - all queries handled above
        raise RuntimeError("Query should have been handled by Privacy Analyst Agent")
        
        # 그래프 파일 확인
        graphml_path = os.path.join(self.working_dir, "graph_chunk_entity_relation.graphml")
        if os.path.exists(graphml_path):
            import networkx as nx
            G = nx.read_graphml(graphml_path)
            # #region agent log
            with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                revenue_nodes = [n for n,d in G.nodes(data=True) if 'revenue' in str(d).lower() or 'revenue' in str(n).lower()]
                f.write(__import__('json').dumps({"location":"graphrag_engine.py:232","message":"graph stats","data":{"nodes":G.number_of_nodes(),"edges":G.number_of_edges(),"revenue_nodes_count":len(revenue_nodes),"revenue_nodes_sample":revenue_nodes[:5]},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H6"})+'\n')
            # #endregion
            print(f"[DEBUG] 그래프 노드 수: {G.number_of_nodes()}, 엣지 수: {G.number_of_edges()}")
        else:
            print(f"[DEBUG] 그래프 파일이 없어요: {graphml_path}")
        
        if mode == "api":
            print(f"질문 모드: OpenAI API (top_k: {top_k})")
            try:
                # Global 모드: 전체 그래프에서 커뮤니티 리포트 기반 검색 (넓은 범위, revenue 같은 질문에 적합)
                query_param = QueryParam(
                    mode='global',  # local -> global (전체 그래프 검색)
                    top_k=top_k,  # 사용자 지정 top_k 사용
                )
                response = await self.query_rag_api.aquery(question, param=query_param)
                # #region agent log
                with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                    f.write(__import__('json').dumps({"location":"graphrag_engine.py:236","message":"query_rag_api response","data":{"response_length":len(response) if response else 0,"response_preview":response[:200] if response else None},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+'\n')
                # #endregion
                print(f"🔍 [DEBUG] query_rag_api.aquery() 완료! (top_k: {top_k})")
            except Exception as e:
                print(f"❌ [DEBUG] query_rag_api.aquery() 에러: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                raise
        else:
            print(f"💬 질문 모드: Ollama (로컬, top_k: {top_k})")
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
                    top_k=top_k,  # 사용자 지정 top_k 사용
                )
                response = await self.query_rag_local.aquery(question, param=query_param)
                print(f"🔍 [DEBUG] query_rag_local.aquery() 완료! (top_k: {top_k})")
            except Exception as e:
                print(f"❌ [DEBUG] query_rag_local.aquery() 에러: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                raise
        
        # 답변이 비어있거나 "Sorry"로 시작하면 경고
        if not response or response.strip().startswith("Sorry"):
            print("⚠️  그래프에 데이터가 있지만 답변을 생성하지 못했어요.")
            print("💡 더 구체적인 질문을 시도해보세요!")
        
        # return_context=True일 경우 출처 정보 추출
        if return_context:
            ctx = await self._aretrieve_context_from_neo4j(question=question, top_sources=min(top_k, 10))
            sources = ctx.get("sources", [])
            # #region agent log
            with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                f.write(__import__('json').dumps({"location":"graphrag_engine.py:288","message":"context retrieval result","data":{"sources_count":len(sources),"first_source_excerpt":sources[0].get('excerpt','')[:100] if sources else None,"retrieval_backend":ctx.get("retrieval_backend")},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H2,H3"})+'\n')
            # #endregion
            return {
                "answer": response,
                "sources": sources,
                "context": ctx.get("context", ""),
                "retrieval_backend": ctx.get("retrieval_backend", "neo4j"),
            }
        
        return response
    
    async def _aretrieve_context_from_neo4j(self, question: str, top_sources: int = 10) -> Dict:
        """
        Neo4j에서 정밀 근거를 추출해 sources/context 생성.
        실패 시 기존 KV 기반 _extract_sources로 폴백.
        """
        try:
            if self._neo4j_retriever is None:
                self._neo4j_retriever = Neo4jRetriever()
            # #region agent log
            with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                f.write(__import__('json').dumps({"location":"graphrag_engine.py:314","message":"before neo4j retrieval","data":{"question":question,"top_sources":top_sources},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run2","hypothesisId":"H2"})+'\n')
            # #endregion
            result = await asyncio.to_thread(
                self._neo4j_retriever.retrieve,
                question,
                2,   # depth=2 (2-hop+)
                50,  # limit=50 (hard LIMIT)
                top_sources,
            )
            sources = result.get("sources", [])
            # #region agent log
            with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                f.write(__import__('json').dumps({"location":"graphrag_engine.py:326","message":"neo4j retrieval result","data":{"sources_count":len(sources),"context_length":len(result.get("context",""))},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run2","hypothesisId":"H2"})+'\n')
            # #endregion
            
            # Neo4j에서 소스를 못 찾았으면 KV 폴백 실행
            if not sources or len(sources) == 0:
                # #region agent log
                with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                    f.write(__import__('json').dumps({"location":"graphrag_engine.py:333","message":"neo4j returned empty sources, falling back to KV","data":{},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run2","hypothesisId":"H2,H3"})+'\n')
                # #endregion
                print(f"[Neo4jRetriever] Neo4j returned 0 sources, falling back to KV store")
                try:
                    sources = await self._extract_sources(question=question)
                    # #region agent log
                    with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                        f.write(__import__('json').dumps({"location":"graphrag_engine.py:340","message":"kv fallback success","data":{"sources_count":len(sources)},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run2","hypothesisId":"H3"})+'\n')
                    # #endregion
                    return {
                        "context": "",
                        "sources": sources,
                        "retrieval_backend": "kv_fallback",
                    }
                except Exception as e2:
                    # #region agent log
                    with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                        f.write(__import__('json').dumps({"location":"graphrag_engine.py:350","message":"kv fallback also failed","data":{"error":str(e2),"error_type":type(e2).__name__},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run2","hypothesisId":"H3"})+'\n')
                    # #endregion
                    sources = []
                    return {
                        "context": "",
                        "sources": sources,
                        "retrieval_backend": "kv_fallback",
                    }
            
            return {
                "context": result.get("context", ""),
                "sources": sources,
                "retrieval_backend": "neo4j",
            }
        except Exception as e:
            # #region agent log
            with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                import traceback
                f.write(__import__('json').dumps({"location":"graphrag_engine.py:337","message":"neo4j retrieval failed, trying fallback","data":{"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()[:500]},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run2","hypothesisId":"H2,H3"})+'\n')
            # #endregion
            print(f"[Neo4jRetriever] fallback to kv sources: {type(e).__name__}: {e}")
            try:
                sources = await self._extract_sources(question=question)
                # #region agent log
                with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                    f.write(__import__('json').dumps({"location":"graphrag_engine.py:347","message":"kv fallback success","data":{"sources_count":len(sources)},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run2","hypothesisId":"H3"})+'\n')
                # #endregion
            except Exception as e2:
                # #region agent log
                with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                    f.write(__import__('json').dumps({"location":"graphrag_engine.py:353","message":"kv fallback also failed","data":{"error":str(e2),"error_type":type(e2).__name__},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run2","hypothesisId":"H3"})+'\n')
                # #endregion
                sources = []
            return {
                "context": "",
                "sources": sources,
                "retrieval_backend": "kv_fallback",
            }
    
    async def _extract_sources(self, question: str = "") -> list[dict]:
        """
        text_chunks KV store에서 출처 정보 추출
        질문과 관련된 청크를 우선 선택 (최대 10개)
        
        Args:
            question: 질문 내용 (관련 청크를 찾기 위해 사용)
        
        Returns:
            List of source dicts with id, file, chunk_id, excerpt
        """
        import json
        import re
        
        sources = []
        text_chunks_path = os.path.join(self.working_dir, "kv_store_text_chunks.json")
        
        if not os.path.exists(text_chunks_path):
            print("[DEBUG] text_chunks 파일이 없어요")
            return sources
        
        # data_sources.json에서 파일명 가져오기
        data_sources_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_sources.json")
        pdf_files = []
        if os.path.exists(data_sources_file):
            try:
                with open(data_sources_file, 'r', encoding='utf-8') as f:
                    data_sources = json.load(f)
                    pdf_files = [pdf.get('name', 'uploaded_document.pdf') for pdf in data_sources.get('pdfs', [])]
            except:
                pass
        
        try:
            with open(text_chunks_path, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
            
            # 질문에서 키워드 추출 (한글/영문)
            question_lower = question.lower()
            keywords = []
            # 주요 키워드 추출
            if "엔비디아" in question or "nvidia" in question_lower:
                keywords.extend(["nvidia", "엔비디아", "NVIDIA"])
            if "수익" in question or "revenue" in question_lower:
                keywords.extend(["revenue", "수익", "Revenue", "REVENUE"])
            if "올해" in question or "2024" in question or "fiscal" in question_lower:
                keywords.extend(["2024", "FY2024", "fiscal"])
            
            # 모든 청크를 순회하며 관련성 점수 계산
            scored_chunks = []
            for chunk_id, chunk_info in chunks_data.items():
                content = chunk_info.get('content', '').lower()
                score = 0
                
                # 키워드 매칭 점수 계산
                for keyword in keywords:
                    if keyword.lower() in content:
                        score += 10
                
                # 질문의 주요 단어가 포함된 경우 추가 점수
                question_words = re.findall(r'\b\w+\b', question_lower)
                for word in question_words:
                    if len(word) > 2 and word in content:
                        score += 1
                
                scored_chunks.append((score, chunk_id, chunk_info))
            
            # 점수 순으로 정렬 (높은 점수 우선)
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            
            # 상위 10개 선택
            top_chunks = scored_chunks[:10]
            
            for idx, (score, chunk_id, chunk_info) in enumerate(top_chunks, 1):
                excerpt = chunk_info.get('content', '')[:300]  # 처음 300자만
                
                # 파일명 결정: data_sources에서 가져오거나 기본값 사용
                file_name = "uploaded_document.pdf"
                if pdf_files:
                    # 여러 파일이 있으면 첫 번째 파일 사용 (또는 청크 ID 기반으로 매핑)
                    file_name = pdf_files[0] if len(pdf_files) == 1 else pdf_files[idx % len(pdf_files)]
                
                # 메타데이터 추출 (있는 경우)
                page_number = chunk_info.get('page_number', 0)
                original_sentence = chunk_info.get('original_sentence', excerpt)
                
                sources.append({
                    "id": idx,
                    "file": file_name,
                    "chunk_id": chunk_id,
                    "excerpt": excerpt,
                    "tokens": chunk_info.get('tokens', 0),
                    "page_number": page_number,
                    "original_sentence": original_sentence
                })
            
            print(f"[DEBUG] {len(sources)}개의 출처 추출 완료 (질문: {question[:50]}...)")
            
        except Exception as e:
            print(f"[DEBUG] 출처 추출 중 에러: {e}")
        
        return sources
    
    async def aglobal_search(self, question: str, top_k: int = 5, temperature: float = 0.2) -> Dict:
        """
        전체 그래프의 Community Summary를 활용한 전역 검색
        
        "이 모든 문서들의 공통 리스크는?" 같은 질문에 대응
        
        Args:
            question: 사용자 질문
            top_k: 반환할 커뮤니티 수
            temperature: LLM temperature
            
        Returns:
            {
                "answer": str,
                "sources": List[dict],
                "search_type": "global"
            }
        """
        print(f"[GLOBAL SEARCH] 전역 검색 시작: {question}")
        
        # nano-graphrag의 global search mode 활용
        query_param = QueryParam(
            mode="global",  # global mode
            only_need_context=False,
            top_k=top_k
        )
        
        # Community reports 로드
        community_reports = self._load_community_reports()
        
        # LLM으로 전체 요약 생성
        response = await self.query_rag_api.aquery(
            question,
            param=query_param
        )
        
        # 커뮤니티 소스 추출
        sources = self._extract_community_sources(community_reports, top_k)
        
        print(f"[GLOBAL SEARCH] 완료: {len(sources)}개 커뮤니티 참조")
        
        return {
            "answer": response,
            "sources": sources,
            "search_type": "global"
        }
    
    def _load_community_reports(self) -> Dict:
        """kv_store_community_reports.json 로드"""
        import json
        reports_path = os.path.join(self.working_dir, "kv_store_community_reports.json")
        
        if not os.path.exists(reports_path):
            print("[DEBUG] community_reports 파일이 없어요")
            return {}
        
        try:
            with open(reports_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[DEBUG] community_reports 로드 중 에러: {e}")
            return {}
    
    def _extract_community_sources(self, community_reports: Dict, top_k: int = 5) -> List[Dict]:
        """커뮤니티 리포트에서 소스 정보 추출"""
        sources = []
        
        # 커뮤니티 리포트를 소스로 변환
        for idx, (community_id, report_data) in enumerate(list(community_reports.items())[:top_k], 1):
            # report_data에서 실제 텍스트 추출
            if isinstance(report_data, dict):
                # 'report_string' 키가 있으면 사용
                if 'report_string' in report_data:
                    content = report_data['report_string']
                # 'content' 키가 있으면 사용
                elif 'content' in report_data:
                    content = report_data['content']
                # 그 외의 경우 전체를 문자열로
                else:
                    content = str(report_data)
            else:
                content = str(report_data)
            
            # 커뮤니티 제목 추출 (첫 번째 줄의 # 제거)
            lines = content.split('\n')
            title = lines[0].replace('#', '').strip() if lines else "Community Summary"
            
            # 내용 요약 (첫 3줄 정도)
            excerpt = '\n'.join(lines[:3]) if len(lines) > 1 else content[:300]
            
            sources.append({
                "id": idx,
                "file": f"Community {community_id}: {title[:50]}",
                "chunk_id": community_id,
                "excerpt": excerpt[:400],
                "page_number": 0,
                "original_sentence": content[:1000],  # 전체 내용 (최대 1000자)
                "type": "community"
            })
        
        return sources
    
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
    
    async def _convert_to_domain_nodes(self) -> None:
        """
        Entity를 Event/Actor/Asset/Factor/Region으로 변환
        
        단계:
        1. GraphML에서 Entity 읽기
        2. EntityClassifier로 분류
        3. Neo4j에 도메인 노드 생성
        4. 관계 추론 (TRIGGERS, IMPACTS, INVOLVED_IN, LOCATED_IN)
        """
        try:
            import networkx as nx
            
            # Lazy loading
            if self._entity_classifier is None:
                self._entity_classifier = EntityClassifier()
            if self._relationship_inferencer is None:
                self._relationship_inferencer = RelationshipInferencer()
            if self._neo4j_db is None:
                self._neo4j_db = Neo4jDatabase()
            
            # 1. GraphML에서 Entity 읽기
            graphml_path = os.path.join(self.working_dir, "graph_chunk_entity_relation.graphml")
            if not os.path.exists(graphml_path):
                print("⚠️  GraphML 파일이 없어서 도메인 노드 변환을 건너뜁니다.")
                return
            
            G = nx.read_graphml(graphml_path)
            
            # Entity 노드만 필터링
            entity_nodes = [
                (node_id, data)
                for node_id, data in G.nodes(data=True)
                if data.get('entity_type') == 'entity' or 'entity_name' in data
            ]
            
            if not entity_nodes:
                print("⚠️  Entity 노드가 없어서 도메인 노드 변환을 건너뜁니다.")
                return
            
            print(f"📊 {len(entity_nodes)}개의 Entity 노드 발견")
            
            # 2. Entity 분류
            entities_to_classify = []
            for node_id, data in entity_nodes[:50]:  # 최대 50개만 처리 (메모리 절약)
                entities_to_classify.append({
                    "id": node_id,
                    "name": data.get('entity_name', node_id),
                    "type": data.get('entity_type', 'unknown'),
                    "description": data.get('description', '')
                })
            
            print(f"🔍 {len(entities_to_classify)}개의 Entity 분류 시작...")
            classifications = await self._entity_classifier.classify_batch(entities_to_classify)
            
            # 3. Neo4j에 도메인 노드 생성
            domain_nodes = {
                "Event": [],
                "Actor": [],
                "Asset": [],
                "Factor": [],
                "Region": []
            }
            
            for entity, classification in zip(entities_to_classify, classifications):
                category = classification.get("category", "None")
                confidence = classification.get("confidence", 0.0)
                
                # 신뢰도가 0.6 이상인 경우만 생성
                if confidence < 0.6 or category == "None":
                    continue
                
                # 노드 속성 추론
                node_properties = self._entity_classifier.infer_node_properties(
                    entity_name=entity["name"],
                    category=category,
                    entity_data=entity
                )
                
                # Neo4j에 노드 생성
                try:
                    await asyncio.to_thread(
                        self._neo4j_db.create_domain_node,
                        node_type=category,
                        node_id=entity["id"],
                        node_data=node_properties
                    )
                    
                    # 노드 정보 저장 (관계 추론용)
                    domain_nodes[category].append({
                        "id": entity["id"],
                        **node_properties
                    })
                    
                    print(f"  ✅ {category} 노드 생성: {entity['name']} (신뢰도: {confidence:.2f})")
                    
                except Exception as e:
                    print(f"  ⚠️  {category} 노드 생성 실패: {entity['name']} - {e}")
            
            # 통계 출력
            total_nodes = sum(len(nodes) for nodes in domain_nodes.values())
            print(f"\n📊 도메인 노드 생성 완료: 총 {total_nodes}개")
            for category, nodes in domain_nodes.items():
                if nodes:
                    print(f"  - {category}: {len(nodes)}개")
            
            # 4. 관계 추론 (Event, Factor, Asset이 있을 때만)
            if domain_nodes["Event"] and domain_nodes["Factor"]:
                print("\n🔗 관계 추론 시작...")
                
                # Event → Factor (TRIGGERS)
                for event in domain_nodes["Event"][:10]:  # 최대 10개만
                    triggers = await self._relationship_inferencer.infer_triggers(
                        event=event,
                        factors=domain_nodes["Factor"]
                    )
                    
                    for rel in triggers:
                        try:
                            await asyncio.to_thread(
                                self._neo4j_db.create_domain_relationship,
                                rel_type=rel["type"],
                                source_id=rel["source_id"],
                                target_id=rel["target_id"],
                                source_label=rel["source_label"],
                                target_label=rel["target_label"],
                                rel_data=rel
                            )
                            print(f"  ✅ TRIGGERS 관계 생성: {event['name']} → Factor")
                        except Exception as e:
                            print(f"  ⚠️  TRIGGERS 관계 생성 실패: {e}")
                
                # Factor → Asset (IMPACTS)
                if domain_nodes["Asset"]:
                    for factor in domain_nodes["Factor"][:10]:  # 최대 10개만
                        impacts = await self._relationship_inferencer.infer_impacts(
                            factor=factor,
                            assets=domain_nodes["Asset"]
                        )
                        
                        for rel in impacts:
                            try:
                                await asyncio.to_thread(
                                    self._neo4j_db.create_domain_relationship,
                                    rel_type=rel["type"],
                                    source_id=rel["source_id"],
                                    target_id=rel["target_id"],
                                    source_label=rel["source_label"],
                                    target_label=rel["target_label"],
                                    rel_data=rel
                                )
                                print(f"  ✅ IMPACTS 관계 생성: Factor → {rel.get('direction', 'Unknown')} Asset")
                            except Exception as e:
                                print(f"  ⚠️  IMPACTS 관계 생성 실패: {e}")
                
                print("✅ 도메인 노드 변환 완료!")
            else:
                print("⚠️  Event 또는 Factor가 없어서 관계 추론을 건너뜁니다.")
        
        except Exception as e:
            print(f"❌ 도메인 노드 변환 중 에러: {e}")
            import traceback
            traceback.print_exc()


# Backward compatibility alias
HybridGraphRAGEngine = PrivacyGraphRAGEngine
