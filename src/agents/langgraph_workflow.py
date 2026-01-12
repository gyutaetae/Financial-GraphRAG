"""
LangGraph 기반 Agentic Workflow
Planner → Collector → Analyst → Writer 순차 실행
Feedback Loop: Analyst가 정보 부족 감지 시 Collector로 회귀
"""

import uuid
from typing import TypedDict, List, Dict, Annotated, Literal
from langgraph.graph import StateGraph, END, add_messages

from .agent_context import AgentContext, QueryComplexity
from .planner_agent import PlannerAgent
from .kb_collector_agent import KBCollectorAgent
from .analyst_agent import AnalystAgent
from .writer_agent import WriterAgent
from .memory_manager import get_memory_manager


class AgenticState(TypedDict):
    """
    LangGraph State 정의
    
    AgentContext 기반 확장
    """
    # 기본 정보
    question: str
    session_id: str
    
    # 워크플로우 제어
    subtasks: List[Dict]
    iteration_count: int
    needs_more_info: bool
    max_iterations: int
    
    # 에이전트 결과
    sources: List[Dict]
    validated_data: List[Dict]
    final_report: str
    reasoning_path: List[str]
    confidence: float
    recommendation: str
    
    # 메타데이터
    neo4j_keys: List[str]
    processing_steps: List[str]
    messages: Annotated[list, add_messages]


class AgenticWorkflow:
    """
    LangGraph 워크플로우 관리자
    
    역할:
    1. State 관리
    2. 노드 실행
    3. Conditional Edge 라우팅
    4. 메모리 최적화
    """
    
    def __init__(self, engine=None, mcp_manager=None, neo4j_db=None):
        """
        Args:
            engine: HybridGraphRAGEngine 인스턴스
            mcp_manager: MCP Manager 인스턴스
            neo4j_db: Neo4jDatabase 인스턴스
        """
        # #region agent log
        import json
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"langgraph_workflow.py:56","message":"AgenticWorkflow init entry","data":{"has_engine":engine is not None,"has_mcp":mcp_manager is not None,"has_neo4j":neo4j_db is not None},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H2,H3"})+'\n')
        # #endregion
        self.engine = engine
        self.mcp_manager = mcp_manager
        self.neo4j_db = neo4j_db
        self.memory_manager = get_memory_manager()
        
        # 에이전트 초기화
        # #region agent log
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"langgraph_workflow.py:67","message":"Before agent init","data":{},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H3"})+'\n')
        # #endregion
        self.planner = PlannerAgent()
        self.collector = KBCollectorAgent(
            engine=engine, 
            web_search_enabled=True, 
            mcp_manager=mcp_manager,
            neo4j_db=neo4j_db
        )
        self.analyst = AnalystAgent(
            mcp_manager=mcp_manager,
            neo4j_db=neo4j_db
        )
        self.writer = WriterAgent(neo4j_db=neo4j_db)
        # #region agent log
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"langgraph_workflow.py:82","message":"After agent init","data":{},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H3"})+'\n')
        # #endregion
        
        # 그래프 구축
        # #region agent log
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"langgraph_workflow.py:85","message":"Before graph build","data":{},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H3"})+'\n')
        # #endregion
        self.graph = self._build_graph()
        # #region agent log
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"langgraph_workflow.py:90","message":"After graph build","data":{"graph_ready":self.graph is not None},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H3"})+'\n')
        # #endregion
    
    def _build_graph(self) -> StateGraph:
        """
        LangGraph 워크플로우 그래프 구축
        
        Returns:
            컴파일된 StateGraph
        """
        workflow = StateGraph(AgenticState)
        
        # 노드 추가
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("collector", self._collector_node)
        workflow.add_node("analyst", self._analyst_node)
        workflow.add_node("writer", self._writer_node)
        
        # 엣지 정의
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "collector")
        workflow.add_edge("collector", "analyst")
        
        # Conditional Edge: Analyst → Collector or Writer
        workflow.add_conditional_edges(
            "analyst",
            self._should_collect_more,
            {
                "collector": "collector",  # 정보 부족 → 재수집
                "writer": "writer"         # 충분 → 리포트 작성
            }
        )
        
        workflow.add_edge("writer", END)
        
        return workflow.compile()
    
    async def _planner_node(self, state: AgenticState) -> AgenticState:
        """
        Planner 노드: 질문 분해
        
        Args:
            state: 현재 상태
            
        Returns:
            subtasks가 채워진 상태
        """
        print("[Planner] 질문 분해 시작...")
        
        # AgentContext 생성
        context = self._state_to_context(state)
        
        # Planner 실행
        context = await self.planner.execute(context)
        
        # State 업데이트
        state["subtasks"] = context.subtasks
        state["processing_steps"].extend(context.processing_steps)
        
        # 메모리 정리
        self.memory_manager.flush_llm_memory("Planner")
        
        print(f"[Planner] {len(context.subtasks)}개 서브태스크 생성 완료")
        return state
    
    async def _collector_node(self, state: AgenticState) -> AgenticState:
        """
        KB Collector 노드: 정보 수집
        
        Args:
            state: 현재 상태
            
        Returns:
            sources가 채워진 상태
        """
        print(f"[Collector] 정보 수집 시작 (반복 {state['iteration_count']+1}회)...")
        
        # AgentContext 생성
        context = self._state_to_context(state)
        
        # Collector 실행
        context = await self.collector.execute(context)
        
        # State 업데이트
        state["sources"] = context.sources
        state["neo4j_keys"] = context.neo4j_keys
        state["processing_steps"].extend(context.processing_steps)
        
        # 메모리 정리
        self.memory_manager.flush_llm_memory("Collector")
        
        print(f"[Collector] {len(context.sources)}개 소스 수집 완료")
        return state
    
    async def _analyst_node(self, state: AgenticState) -> AgenticState:
        """
        Analyst 노드: 데이터 검증 및 충분성 판단
        
        Args:
            state: 현재 상태
            
        Returns:
            validated_data, needs_more_info가 채워진 상태
        """
        print("[Analyst] 데이터 검증 시작...")
        
        # AgentContext 생성
        context = self._state_to_context(state)
        
        # Analyst 실행
        context = await self.analyst.execute(context)
        
        # State 업데이트
        state["validated_data"] = context.validated_data
        state["confidence"] = context.confidence
        state["needs_more_info"] = context.needs_more_info
        state["processing_steps"].extend(context.processing_steps)
        
        # 반복 횟수 증가
        state["iteration_count"] += 1
        
        # 메모리 정리
        self.memory_manager.flush_llm_memory("Analyst")
        
        print(f"[Analyst] 검증 완료 (신뢰도: {context.confidence:.0%}, 충분성: {not context.needs_more_info})")
        return state
    
    async def _writer_node(self, state: AgenticState) -> AgenticState:
        """
        Writer 노드: 최종 리포트 작성
        
        Args:
            state: 현재 상태
            
        Returns:
            final_report, reasoning_path가 채워진 상태
        """
        print("[Writer] 리포트 작성 시작...")
        
        # AgentContext 생성
        context = self._state_to_context(state)
        
        # Writer 실행
        context = await self.writer.execute(context)
        
        # State 업데이트
        state["final_report"] = context.final_report
        state["recommendation"] = context.recommendation or "HOLD"
        state["reasoning_path"] = context.reasoning_path
        state["confidence"] = context.confidence
        state["processing_steps"].extend(context.processing_steps)
        
        # 메모리 정리
        self.memory_manager.flush_llm_memory("Writer")
        
        print(f"[Writer] 리포트 작성 완료 (추천: {state['recommendation']})")
        return state
    
    def _should_collect_more(self, state: AgenticState) -> Literal["collector", "writer"]:
        """
        Conditional Edge: 정보 재수집 여부 판단
        
        Args:
            state: 현재 상태
            
        Returns:
            "collector" (재수집) or "writer" (작성)
        """
        # 최대 반복 횟수 체크
        if state["iteration_count"] >= state["max_iterations"]:
            print(f"[Router] 최대 반복 횟수 도달 ({state['max_iterations']}회) → Writer")
            return "writer"
        
        # 정보 부족 여부
        if state["needs_more_info"]:
            print(f"[Router] 정보 부족 감지 → Collector 재실행")
            return "collector"
        
        print(f"[Router] 정보 충분 → Writer")
        return "writer"
    
    def _state_to_context(self, state: AgenticState) -> AgentContext:
        """
        LangGraph State를 AgentContext로 변환
        
        Args:
            state: LangGraph 상태
            
        Returns:
            AgentContext 인스턴스
        """
        context = AgentContext(
            question=state["question"],
            complexity=QueryComplexity.MODERATE,
            enable_web_search=True
        )
        
        # State의 데이터를 Context에 복사
        context.subtasks = state.get("subtasks", [])
        context.iteration_count = state.get("iteration_count", 0)
        context.neo4j_keys = state.get("neo4j_keys", [])
        context.needs_more_info = state.get("needs_more_info", False)
        
        context.sources = state.get("sources", [])
        context.validated_data = state.get("validated_data", [])
        context.confidence = state.get("confidence", 0.0)
        context.reasoning_path = state.get("reasoning_path", [])
        
        context.processing_steps = state.get("processing_steps", [])
        
        return context
    
    async def run(self, question: str, max_iterations: int = 3) -> Dict:
        """
        워크플로우 실행
        
        Args:
            question: 사용자 질문
            max_iterations: 최대 Feedback Loop 반복 횟수
            
        Returns:
            최종 결과 딕셔너리
        """
        # 초기 상태 생성
        initial_state: AgenticState = {
            "question": question,
            "session_id": str(uuid.uuid4())[:8],
            "subtasks": [],
            "iteration_count": 0,
            "needs_more_info": False,
            "max_iterations": max_iterations,
            "sources": [],
            "validated_data": [],
            "final_report": "",
            "reasoning_path": [],
            "confidence": 0.0,
            "recommendation": "HOLD",
            "neo4j_keys": [],
            "processing_steps": [],
            "messages": []
        }
        
        print(f"\n{'='*60}")
        print(f"Agentic Workflow 시작: {question}")
        print(f"Session ID: {initial_state['session_id']}")
        print(f"{'='*60}\n")
        
        # 그래프 실행
        final_state = await self.graph.ainvoke(initial_state)
        
        # 결과 반환
        return {
            "answer": final_state["final_report"],
            "sources": final_state["sources"],
            "confidence": final_state["confidence"],
            "recommendation": final_state["recommendation"],
            "reasoning_path": final_state["reasoning_path"],
            "subtasks": final_state["subtasks"],
            "iteration_count": final_state["iteration_count"],
            "processing_steps": final_state["processing_steps"],
            "mode": "AGENTIC_WORKFLOW"
        }
