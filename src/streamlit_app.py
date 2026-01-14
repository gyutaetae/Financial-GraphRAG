import streamlit as st
import requests
import sys
import os
import json
import time
import re
from typing import List, Dict

# .env 파일 읽기
from dotenv import load_dotenv
load_dotenv()

# Health Check 모듈 임포트
try:
    from health_check import HealthChecker
    HEALTH_CHECK_AVAILABLE = True
except ImportError:
    HEALTH_CHECK_AVAILABLE = False
    HealthChecker = None

# 환경 변수 읽기 (하이브리드 클라우드 지원)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Neo4j 연결 체크 함수 (레거시 호환)
def check_neo4j_connection():
    """Neo4j 데이터베이스 연결 상태 확인"""
    if HEALTH_CHECK_AVAILABLE:
        checker = HealthChecker()
        return checker.check_neo4j()
    
    # Fallback: 기본 체크
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        driver.close()
        return True, "✅ Neo4j Connected"
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower():
            return False, "❌ Neo4j 인증 실패"
        elif "dns" in error_msg.lower():
            return False, "❌ Neo4j 주소 오류"
        else:
            return False, f"❌ Neo4j: {error_msg[:50]}"

# 현재 파일의 폴더 경로를 추가해요!
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Streamlit Cloud용 직접 엔진 임포트
try:
    from engine import HybridGraphRAGEngine
    DIRECT_ENGINE_AVAILABLE = True
except ImportError:
    DIRECT_ENGINE_AVAILABLE = False
    HybridGraphRAGEngine = None

# 페이지 설정 - Executive Dashboard
st.set_page_config(
    page_title="VIK AI: Executive Intelligence",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Dark Mode 스타일 CSS
st.markdown("""
<style>
/* 전체 앱 다크모드 스타일 */
.stApp {
    background-color: #0e1117;
    color: #ffffff;
}

/* 모든 텍스트 기본 색상 */
.stApp, .stApp p, .stApp span, .stApp div {
    color: #ffffff !important;
}

/* 보고서 컨테이너 다크모드 */
.report-container {
    background: #1a1d29;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    margin: 1.5rem 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.7;
    border: 1px solid #2d3142;
}

.report-container h2 {
    color: #ffffff !important;
    font-size: 1.5rem;
    font-weight: 600;
    margin-top: 2rem;
    margin-bottom: 1rem;
    border-bottom: 2px solid #3d4461;
    padding-bottom: 0.5rem;
}

.report-container p {
    color: #e0e0e0 !important;
    margin-bottom: 1rem;
    font-size: 1rem;
}

/* 인라인 citation 스타일 - 호버링 가능 */
.citation {
    display: inline-block;
    background: #4a9eff;
    color: #ffffff;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.85em;
    font-weight: 600;
    margin: 0 2px;
    cursor: pointer;
    text-decoration: none;
    position: relative;
    transition: all 0.2s ease;
}

.citation:hover {
    background: #6bb3ff;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(74,158,255,0.5);
}

/* 툴팁 다크모드 스타일 */
.citation-tooltip {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    z-index: 1000;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    min-width: 320px;
    max-width: 400px;
    background: #1e2330;
    border: 1px solid #3d4461;
    border-radius: 8px;
    padding: 12px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.6);
    transition: opacity 0.3s ease, visibility 0.3s ease;
    pointer-events: none;
}

.citation:hover .citation-tooltip,
.citation-tooltip:hover {
    visibility: visible;
    opacity: 1;
    pointer-events: auto;
}

.citation-tooltip::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: #1e2330 transparent transparent transparent;
}

.tooltip-header {
    font-weight: 600;
    color: #4a9eff !important;
    font-size: 0.9em;
    margin-bottom: 6px;
    border-bottom: 1px solid #3d4461;
    padding-bottom: 4px;
}

.tooltip-content {
    font-size: 0.85em;
    color: #c0c0c0 !important;
    line-height: 1.4;
}

.tooltip-meta {
    font-size: 0.75em;
    color: #888888 !important;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid #2d3142;
}

/* References 섹션 다크모드 */
.references {
    background: #1a1d29;
    border-left: 3px solid #4a9eff;
    padding: 1rem 1.5rem;
    margin-top: 2rem;
    border-radius: 4px;
}

.references h3 {
    color: #ffffff !important;
    font-size: 1.2rem;
    margin-bottom: 1rem;
}

.reference-item {
    margin-bottom: 0.8rem;
    padding: 0.5rem;
    background: #252936;
    border-radius: 4px;
    border: 1px solid #2d3142;
}

.reference-number {
    display: inline-block;
    background: #4a9eff;
    color: #ffffff;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    margin-right: 0.5rem;
    font-size: 0.9em;
}

.reference-file {
    font-weight: 500;
    color: #e0e0e0 !important;
}

.reference-excerpt {
    color: #a0a0a0 !important;
    font-size: 0.9em;
    margin-top: 0.3rem;
    font-style: italic;
}

/* 채팅 메시지 다크모드 */
.user-message {
    background: #1e3a5f !important;
    color: #ffffff !important;
}

.assistant-message {
    background: #1a1d29 !important;
    color: #ffffff !important;
}

/* Streamlit 기본 요소 다크모드 오버라이드 */
.stMarkdown {
    color: #ffffff !important;
}

.stTextInput input {
    background-color: #1a1d29 !important;
    color: #ffffff !important;
    border: 1px solid #3d4461 !important;
}

.stTextArea textarea {
    background-color: #1a1d29 !important;
    color: #ffffff !important;
    border: 1px solid #3d4461 !important;
}

.stButton button {
    background-color: #4a9eff !important;
    color: #ffffff !important;
    border: none !important;
}

.stButton button:hover {
    background-color: #6bb3ff !important;
}

/* 탭 스타일 다크모드 */
.stTabs [data-baseweb="tab-list"] {
    background-color: #1a1d29;
}

.stTabs [data-baseweb="tab"] {
    color: #a0a0a0 !important;
}

.stTabs [aria-selected="true"] {
    color: #4a9eff !important;
}

/* 익스팬더 다크모드 */
.streamlit-expanderHeader {
    background-color: #1a1d29 !important;
    color: #ffffff !important;
}

.streamlit-expanderContent {
    background-color: #0e1117 !important;
    border: 1px solid #2d3142 !important;
}

/* 슬라이더 다크모드 */
.stSlider label {
    color: #ffffff !important;
}

/* 라디오 버튼 다크모드 */
.stRadio label {
    color: #ffffff !important;
}

/* 체크박스 다크모드 */
.stCheckbox label {
    color: #ffffff !important;
}

/* 캡션 다크모드 */
.stCaptionContainer, .stCaption {
    color: #a0a0a0 !important;
}

/* 파일 업로더 다크모드 */
.stFileUploader {
    background-color: #1a1d29 !important;
    border: 1px solid #3d4461 !important;
}

/* 정보/경고 메시지 다크모드 */
.stAlert {
    background-color: #1a1d29 !important;
    border: 1px solid #3d4461 !important;
}
</style>
""", unsafe_allow_html=True)

# 데이터 소스 관리 파일 경로
DATA_SOURCES_FILE = os.path.join(os.path.dirname(__file__), "data_sources.json")

def load_data_sources():
    try:
        if os.path.exists(DATA_SOURCES_FILE):
            with open(DATA_SOURCES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 누락된 키가 있으면 추가
                if "pdf" not in data:
                    data["pdf"] = []
                if "text" not in data:
                    data["text"] = []
                if "url" not in data:
                    data["url"] = []
                return data
        return {"pdf": [], "text": [], "url": []}
    except Exception as e:
        print(f"Error loading data sources: {e}")
        return {"pdf": [], "text": [], "url": []}

def save_data_sources(data):
    with open(DATA_SOURCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _clean_excerpt(text: str) -> str:
    """레퍼런스에 표시할 excerpt를 사람이 읽기 좋게 정리"""
    if not text:
        return ""
    # 제어문자 제거
    text = re.sub(r'[\x00-\x1F\x7F]', ' ', str(text))
    # 너무 깨진 문자(�) 제거
    text = text.replace("�", " ")
    # 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    # 첫 문장만 사용 (., ?, !, 한국어 종결어미 기준)
    sentence_split = re.split(r'(?<=[\.\?\!])\s+|(?<=[다요])\s+', text)
    first = sentence_split[0] if sentence_split else text
    return first[:300]

def _strip_llm_sources_section(text: str) -> str:
    """
    LLM이 답변 말미에 'Sources:' / 'References:' 같은 섹션을 텍스트로 붙이는 경우,
    UI에서 HTML References를 별도로 렌더링하므로 해당 섹션을 제거한다.
    """
    if not text:
        return text
    # 흔한 패턴: "\n\nSources:\n..." 또는 "\n\nReferences:\n..."
    m = re.search(r"\n\s*\n\s*(Sources|Source|References|Reference)\s*:\s*\n", text, flags=re.IGNORECASE)
    if m:
        return text[:m.start()].rstrip()
    return text

def render_report_with_citations(answer: str, sources: List[Dict]) -> str:
    """
    답변 텍스트에 인라인 citation 번호를 감지하고, 
    호버 시 툴팁을 보여주는 HTML로 변환
    """
    # Citation 패턴 찾기: [1], [2], etc.
    citation_pattern = r'\[(\d+)\]'
    
    def replace_citation(match):
        cite_num = int(match.group(1))
        # 해당 번호의 source 찾기
        source = next((s for s in sources if s.get('id') == cite_num), None)
        
        if source:
            file_name = source.get('file', 'Unknown')
            source_type = source.get('type', 'document')
            page_num = source.get('page_number', 'N/A')
            
            # 원문 추출 - 딕셔너리가 아닌 실제 텍스트만
            original = source.get('original_sentence', source.get('excerpt', ''))
            if isinstance(original, dict):
                # 딕셔너리인 경우 'report_string' 추출
                original = original.get('report_string', str(original))
            excerpt = _clean_excerpt(original)
            
            # Community Summary인 경우 표시 방식 조정
            if source_type == 'community':
                display_name = file_name.split(':')[1].strip() if ':' in file_name else file_name
                tooltip_meta = "Community Report"
            else:
                display_name = file_name
                tooltip_meta = f"Page {page_num}"
            
            # 툴팁이 포함된 citation 링크 생성
            # NOTE: markdown에서 4칸 이상 들여쓰기는 code block으로 취급될 수 있어
            # 줄바꿈/들여쓰기를 최소화한다.
            return (
                f'<a href="#source-{cite_num}" class="citation">'
                f'[{cite_num}]'
                f'<div class="citation-tooltip">'
                f'<div class="tooltip-header">{display_name}</div>'
                f'<div class="tooltip-content">{excerpt}...</div>'
                f'<div class="tooltip-meta">{tooltip_meta}</div>'
                f'</div>'
                f'</a>'
            )
        return match.group(0)
    # Citation을 HTML로 변환
    html_answer = re.sub(citation_pattern, replace_citation, answer)
    
    # References 섹션 생성
    references_html = '<div class="references"><h3>References</h3>'
    for source in sources:
        cite_id = source.get('id')
        file_name = source.get('file', 'Unknown')
        source_type = source.get('type', 'document')
        page_num = source.get('page_number', 'N/A')
        
        # 원문 추출 - 딕셔너리가 아닌 실제 텍스트만
        original = source.get('original_sentence', source.get('excerpt', ''))
        if isinstance(original, dict):
            original = original.get('report_string', str(original))
        excerpt = _clean_excerpt(original)
        
        # Community Summary인 경우 표시 방식 조정
        if source_type == 'community':
            display_name = file_name
            meta_info = "Community Report"
        else:
            display_name = file_name
            meta_info = f"Page {page_num}"
        
        references_html += (
            f'<div class="reference-item" id="source-{cite_id}">'
            f'<span class="reference-number">[{cite_id}]</span> '
            f'<span class="reference-file">{display_name}</span> ({meta_info})'
            f'<div class="reference-excerpt">"{excerpt}..."</div>'
            f'</div>'
        )
    references_html += '</div>'
    
    # 전체 HTML 조합
    full_html = f'<div class="report-container">{html_answer}{references_html}</div>'
    
    return full_html

def render_citations_with_popover(sources: List[Dict], message_idx: int = 0):
    """
    출처 정보를 Streamlit Popover로 렌더링
    message_idx: 메시지 인덱스를 포함하여 고유한 키 생성
    """
    if not sources:
        return
    
    st.markdown("---")
    st.markdown("### Source Details")
    
    # 각 출처를 expander 또는 popover로 표시
    cols = st.columns(min(len(sources), 3))
    for idx, source in enumerate(sources):
        col_idx = idx % 3
        with cols[col_idx]:
            with st.popover(f"[{source['id']}] {source.get('file', 'Source')[:25]}...", use_container_width=True):
                st.caption(f"**File**: {source.get('file', 'Unknown')}")
                st.caption(f"**Page**: {source.get('page_number', 'N/A')}")
                st.caption(f"**Chunk ID**: {source.get('chunk_id', 'N/A')}")
                
                if source.get('url'):
                    st.caption(f"**URL**: [{source['url']}]({source['url']})")
                
                # 고유한 키: 메시지 인덱스 + 소스 인덱스
                unique_key = f"excerpt_msg{message_idx}_src{idx}_{int(time.time()*1000)}"
                
                st.text_area(
                    "Original Text",
                    value=source.get('original_sentence', source.get('excerpt', ''))[:500],
                    height=150,
                    disabled=True,
                    key=unique_key
                )

# 데이터 소스 삭제 함수
def delete_data_source(source_type, index):
    data_sources = load_data_sources()
    if 0 <= index < len(data_sources[source_type]):
        del data_sources[source_type][index]
        save_data_sources(data_sources)
        return True
    return False

# API 엔드포인트
# Streamlit Cloud에서는 STREAMLIT_SHARING_MODE 환경 변수가 자동으로 설정됨
# 로컬에서는 127.0.0.1:8000, Cloud에서는 API 서버 비활성화
import socket

def is_streamlit_cloud():
    """Streamlit Cloud 환경 감지"""
    return os.getenv("STREAMLIT_SHARING_MODE") is not None or os.getenv("HOSTNAME", "").startswith("streamlit-")

if is_streamlit_cloud():
    # Streamlit Cloud: API 서버 없이 직접 엔진 사용
    API_BASE_URL = None
    USE_DIRECT_ENGINE = True
else:
    # 로컬: FastAPI 서버 사용
    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    USE_DIRECT_ENGINE = False

# 전역 엔진 인스턴스 (Streamlit Cloud용)
_direct_engine = None

def get_direct_engine():
    """Streamlit Cloud에서 직접 엔진 가져오기"""
    global _direct_engine
    if _direct_engine is None and DIRECT_ENGINE_AVAILABLE:
        try:
            _direct_engine = HybridGraphRAGEngine(
                working_dir="./graph_storage_hybrid",
                enable_local=False,  # Streamlit Cloud에서는 Ollama 없음
                enable_neo4j=False   # Streamlit Cloud에서는 Neo4j 없음
            )
        except Exception as e:
            st.error(f"엔진 초기화 실패: {str(e)}")
            return None
    return _direct_engine

# 캐시: 백엔드 상태/질의 (규칙: st.cache_data로 무거운 호출 캐싱)
@st.cache_data(ttl=30, show_spinner=False)
def cached_health(api_base_url) -> bool:
    if USE_DIRECT_ENGINE or api_base_url is None:
        # Streamlit Cloud: 직접 엔진 사용 가능 여부 확인
        return DIRECT_ENGINE_AVAILABLE
    try:
        r = requests.get(f"{api_base_url}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


@st.cache_data(ttl=120, show_spinner=False)
def cached_query(api_base_url: str, payload_json: str) -> Dict:
    payload = json.loads(payload_json)
    
    if USE_DIRECT_ENGINE:
        # Streamlit Cloud: 직접 엔진 사용
        engine = get_direct_engine()
        if engine is None:
            return {"_error": "GraphRAG 엔진을 초기화할 수 없습니다."}
        
        try:
            import asyncio
            question = payload.get("question", "")
            search_type = payload.get("search_type", "local")
            
            # 비동기 함수를 동기적으로 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if search_type == "global":
                response = loop.run_until_complete(engine.aglobal_search(question))
            else:
                response = loop.run_until_complete(engine.aquery(question))
            
            loop.close()
            
            return {
                "response": response,
                "sources": [],
                "confidence": 1.0,
                "search_mode": "DIRECT_ENGINE"
            }
        except Exception as e:
            return {"_error": f"엔진 실행 오류: {str(e)}"}
    
    # 로컬: FastAPI 서버 사용
    # Agentic Workflow 모드 확인
    use_agentic = payload.get("use_agentic_workflow", False)
    endpoint = "/agentic-query" if use_agentic else "/query"
    
    r = requests.post(f"{api_base_url}{endpoint}", json=payload, timeout=180)
    if r.status_code == 200:
        return r.json()
    return {"_error": f"Error {r.status_code}: {r.text}"}

# System Status Bar (Top)
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.markdown("# VIK AI")
    st.markdown("*Powered by GraphRAG*")

with col2:
    server_connected = cached_health(API_BASE_URL)
    
    # Streamlit Cloud 모드일 때는 다른 메시지 표시
    if USE_DIRECT_ENGINE:
        status_text = "Direct Engine Mode"
        status_color = "#28a745"
    else:
        status_text = "Connected" if server_connected else "Backend Disconnected"
        status_color = "#28a745" if server_connected else "#dc3545"
    
    # Neo4j 연결 상태 체크
    neo4j_connected, neo4j_msg = check_neo4j_connection()
    neo4j_color = "#28a745" if neo4j_connected else "#ffc107"
    
    status_html = f"""
    <div style="text-align: right; padding: 10px;">
        <span style="color: {status_color}; font-size: 12px;">
            ● {status_text}
        </span><br>
        <span style="color: {neo4j_color}; font-size: 10px;">
            {neo4j_msg}
        </span>
    </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)

with col3:
    if st.button(" Refresh", type="secondary"):
        st.rerun()

st.markdown("---")

# Main Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Query Interface", "Data Ingestion", "Data Sources", "🏗️ Domain Analysis"])

# Tab 1: Query Interface
with tab1:
    st.markdown("### Query Interface")
    
    # Advanced Settings Expander
    with st.expander("Advanced Settings", expanded=False):
        # Privacy Mode Toggle
        privacy_mode = st.checkbox(
            "Privacy Mode (8GB RAM Optimized)",
            value=st.session_state.get("privacy_mode", False),
            help="Enable offline-first, memory-efficient analysis with Ollama. Perfect for sensitive data."
        )
        st.session_state["privacy_mode"] = privacy_mode
        
        if privacy_mode:
            st.success("Privacy Mode: All processing happens locally with optimized memory usage")
            llm_mode = "LOCAL (qwen2.5-coder-3B)"  # Force LOCAL mode
        else:
            # LLM Mode Selection
            llm_mode = st.radio(
                "LLM Mode",
                ["API (OpenAI)", "LOCAL (qwen2.5-coder-3B)"],
                index=0,
                help="API: Use OpenAI GPT-4o-mini (faster, more accurate) | LOCAL: Use Ollama Qwen2.5-Coder-3B (private, offline)",
                horizontal=True
            )
        
        if llm_mode == "API (OpenAI)":
            st.info("🌐 API Mode: Using OpenAI GPT-4o-mini for high-quality responses")
        else:
            st.info("🏠 LOCAL Mode: Using Ollama Qwen2.5-Coder-3B for privacy-first analysis")
        
        st.markdown("---")
        
        # Search Mode
        search_mode = st.radio(
            "Search Mode",
            ["Local (Specific)", "Global (Overview)"],
            index=0,
            help="Local: Search for specific entities and facts | Global: Get overview and common themes across all documents",
            horizontal=True
        )
        
        st.markdown("---")
        
        # 웹 검색 활성화 토글
        enable_web_search = st.checkbox(
            "Enable Web Search",
            value=False,
            help="Check this to allow AI to search the web for real-time information. Otherwise, it will ONLY use your uploaded PDF documents."
        )
        
        # Multi-Agent 모드 토글
        use_multi_agent = st.checkbox(
            "Multi-Agent Analysis Mode",
            value=False,
            help="Enable 4-agent collaboration (Master → KB Collector → Analyst → Writer) for complex financial queries."
        )
        
        # Agentic Workflow 모드 토글
        use_agentic_workflow = st.checkbox(
            "Agentic Workflow (LangGraph)",
            value=False,
            help="Enable LangGraph-based workflow: Planner → Collector → Analyst → Writer with feedback loop and reasoning path."
        )
        st.session_state["use_agentic_workflow"] = use_agentic_workflow
        
        if enable_web_search:
            st.warning("Web search enabled: AI may search the web for LATEST/TODAY information if needed.")
        else:
            st.info("Document-only mode: AI will answer ONLY from your uploaded PDFs.")
        
        if use_multi_agent:
            st.info("Multi-Agent mode: Master → KB Collector → Analyst → Writer pipeline will process your query.")
        
        if use_agentic_workflow:
            st.success("Agentic Workflow: LangGraph orchestration with automatic feedback loop and reasoning path tracking.")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=0.2,
                step=0.1,
                help="Controls randomness. Lower = more focused, Higher = more creative"
            )
            st.caption(f"Current: {temperature}")
        
        with col2:
            top_k = st.slider(
                "Retrieval Chunks",
                min_value=5,
                max_value=50,
                value=30,
                step=5,
                help="Number of text chunks to retrieve from the knowledge graph"
            )
            st.caption(f"Current: {top_k} chunks")
        
        st.markdown("---")
        st.markdown("**Parameter Guide:**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("""
            **Temperature:**
            - 0.0-0.3: Precise, factual
            - 0.4-0.7: Balanced
            - 0.8-2.0: Creative, diverse
            """)
        with col_b:
            st.markdown("""
            **Retrieval Chunks:**
            - 5-15: Fast, focused
            - 20-30: Balanced (recommended)
            - 35-50: Comprehensive, slower
            """)
    
    # Store settings in session state
    if "temperature" not in st.session_state:
        st.session_state.temperature = 0.2
    if "top_k" not in st.session_state:
        st.session_state.top_k = 30
    if "enable_web_search" not in st.session_state:
        st.session_state.enable_web_search = False
    if "llm_mode" not in st.session_state:
        st.session_state.llm_mode = "api"
    
    st.session_state.temperature = temperature
    st.session_state.top_k = top_k
    st.session_state.enable_web_search = enable_web_search
    st.session_state.use_multi_agent = use_multi_agent
    st.session_state.llm_mode = "api" if "API" in llm_mode else "local"
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Chat container with dark mode styling
    st.markdown("""
    <style>
        .chat-container {
            max-height: 500px;
            overflow-y: auto;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .user-message {
            background: #1e3a5f !important;
            color: #ffffff !important;
            padding: 1rem;
            border-radius: 12px;
            margin: 0.5rem 0 0.5rem auto;
            max-width: 70%;
            text-align: right;
            border: 1px solid #2d4a6f;
        }
        .assistant-message {
            background: #1a1d29 !important;
            color: #ffffff !important;
            padding: 1rem;
            border-radius: 12px;
            margin: 0.5rem auto 0.5rem 0;
            max-width: 70%;
            text-align: left;
            border: 1px solid #2d3142;
        }
        .message-mode {
            font-size: 0.75rem;
            color: #a0a0a0 !important;
            margin-top: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Display chat history with custom styling
    chat_container = st.container()
    with chat_container:
        for msg_idx, message in enumerate(st.session_state.messages):
            if message["role"] == "user":
                st.markdown(f"""
                <div class="user-message">
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                # 출처 정보가 있으면 Perplexity 스타일로 렌더링
                sources = message.get("sources", [])
                source_type = message.get("source_type", "UNKNOWN")
                validation = message.get("validation", None)
                
                # Confidence Score 표시
                if validation and validation.get("confidence_score") is not None:
                    confidence = validation["confidence_score"]
                    if confidence >= 0.9:
                        st.success(f"Confidence: {confidence:.1%} - High reliability")
                    elif confidence >= 0.7:
                        st.info(f"Confidence: {confidence:.1%} - Medium reliability")
                    else:
                        st.warning(f"Confidence: {confidence:.1%} - Low reliability. Some citations may be invalid.")
                
                if sources:                    
                    # LLM이 텍스트로 'Sources:' 섹션을 붙이는 경우 제거 후 렌더링
                    cleaned_content = _strip_llm_sources_section(message["content"])
                    # Citation과 References가 포함된 보고서 형식
                    report_html = render_report_with_citations(cleaned_content, sources)
                    st.markdown(report_html, unsafe_allow_html=True)
                    
                    # Popover로 추가 상세 정보 제공 (선택사항)
                    with st.expander(f"View {len(sources)} Source(s) in Detail", expanded=False):
                        render_citations_with_popover(sources, message_idx=msg_idx)

                    # Evidence(클레임-근거) 표시
                    evidence = message.get("evidence", [])
                    if evidence:
                        with st.expander(f"Evidence ({len(evidence)})", expanded=False):
                            for ev in evidence[:20]:
                                claim_id = ev.get("claim_id")
                                claim_text = ev.get("claim_text", "")
                                citation_ids = ev.get("citation_ids", [])
                                st.markdown(f"- [{claim_id}] {claim_text} " + " ".join([f"[{cid}]" for cid in citation_ids]))
                    
                    # Multi-Agent 추가 정보 표시
                    if message.get("mode") in ["MULTI_AGENT", "AGENTIC_WORKFLOW"]:
                        # 투자 제언
                        recommendation = message.get("recommendation")
                        if recommendation:
                            st.success(f"Investment Recommendation: {recommendation}")
                        
                        # Agentic Workflow 추가 정보
                        if message.get("mode") == "AGENTIC_WORKFLOW":
                            # 추론 경로
                            reasoning_path = message.get("reasoning_path", [])
                            if reasoning_path:
                                with st.expander("Reasoning Path", expanded=True):
                                    for i, step in enumerate(reasoning_path, 1):
                                        st.markdown(f"{i}. {step}")
                            
                            # 서브태스크
                            subtasks = message.get("subtasks", [])
                            if subtasks:
                                with st.expander(f"Subtasks ({len(subtasks)})", expanded=False):
                                    for subtask in subtasks:
                                        st.markdown(f"**{subtask.get('id')}. {subtask.get('task')}** (Target: {subtask.get('target', 'N/A')})")
                                        st.markdown(f"   Priority: {subtask.get('priority', 'N/A')} | Reasoning: {subtask.get('reasoning', 'N/A')}")
                            
                            # 반복 횟수
                            iteration_count = message.get("iteration_count", 0)
                            if iteration_count > 0:
                                st.info(f"Feedback Loop: {iteration_count} iteration(s)")
                        
                        # 핵심 인사이트
                        insights = message.get("insights", [])
                        if insights:
                            with st.expander(f"Key Insights ({len(insights)})", expanded=False):
                                for insight in insights:
                                    st.markdown(f"- {insight}")
                        
                        # 처리 단계
                        processing_steps = message.get("processing_steps", [])
                        if processing_steps:
                            with st.expander("Processing Steps", expanded=False):
                                for step in processing_steps:
                                    st.markdown(f"- {step}")
                else:
                    # 출처 정보가 없으면 기본 형식
                    mode_text = f"<div class='message-mode'>Source: {source_type} | Mode: {message.get('mode', 'N/A')}</div>" if "mode" in message else ""
                    st.markdown(f"""
                    <div class="report-container">
                        {message["content"]}
                        {mode_text}
                    </div>
                    """, unsafe_allow_html=True)
    
    # Clear chat button at the top
    if st.session_state.messages:
        if st.button("Clear Chat History", type="secondary", key="clear_chat_top"):
            st.session_state.messages = []
            st.rerun()
    
    st.markdown("---")
    
    # Chat input at the bottom
    prompt = st.chat_input("Ask a question about your data...")
    
    if prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Get assistant response
        with st.spinner("Generating executive report..."):
            try:
                # Prepare request with advanced parameters
                search_type = "global" if "Global" in search_mode else "local"
                llm_mode_value = st.session_state.get("llm_mode", "api")
                request_data = {
                    "question": prompt,
                    "mode": llm_mode_value,
                    "temperature": st.session_state.get("temperature", 0.2),
                    "top_k": st.session_state.get("top_k", 30),
                    "search_type": search_type,
                    "enable_web_search": st.session_state.get("enable_web_search", False),
                    "use_multi_agent": st.session_state.get("use_multi_agent", False),
                    "use_agentic_workflow": st.session_state.get("use_agentic_workflow", False)
                }
                
                # 캐시된 경로 우선 (동일 질문/파라미터 반복 시 빠름)
                payload_json = json.dumps(request_data, sort_keys=True, ensure_ascii=False)
                result = cached_query(API_BASE_URL, payload_json)

                if "_error" not in result:
                    answer = result.get("answer", "No response generated.")
                    sources = result.get("sources", [])
                    source_type = result.get("source", "UNKNOWN")
                    mode = result.get('mode', 'unknown').upper()
                    validation = result.get("validation", None)
                    evidence = result.get("evidence", [])
                    
                    # Multi-Agent 추가 필드
                    recommendation = result.get("recommendation", None)
                    insights = result.get("insights", [])
                    processing_steps = result.get("processing_steps", [])
                    
                    # Agentic Workflow 추가 필드
                    reasoning_path = result.get("reasoning_path", [])
                    subtasks = result.get("subtasks", [])
                    iteration_count = result.get("iteration_count", 0)
                    
                    # Add assistant response to chat history with sources
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "source_type": source_type,
                        "mode": mode,
                        "validation": validation,
                        "evidence": evidence,
                        "recommendation": recommendation,
                        "insights": insights,
                        "processing_steps": processing_steps,
                        "reasoning_path": reasoning_path,
                        "subtasks": subtasks,
                        "iteration_count": iteration_count
                    })
                else:
                    error_msg = result.get("_error", "Unknown error")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
            except Exception as e:
                error_msg = f"Query failed: {str(e)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
        
        # Rerun to show new messages
        st.rerun()

# Tab 2: Data Ingestion
with tab2:
    st.markdown("### Data Ingestion")
    
    # Check if Privacy Mode is enabled
    privacy_mode_active = st.session_state.get("privacy_mode", False)
    
    if privacy_mode_active:
        input_method = st.radio(
            "Select input method",
            options=["Privacy Upload (JSON/CSV/TXT)", "PDF Upload", "URL Crawling"],
            horizontal=True,
            label_visibility="collapsed"
        )
    else:
        input_method = st.radio(
            "Select input method",
            options=["PDF Upload", "URL Crawling"],
            horizontal=True,
            label_visibility="collapsed"
        )
    
    if input_method == "Privacy Upload (JSON/CSV/TXT)":
        st.info("Privacy Mode: Upload company data files (JSON, CSV, TXT) for local processing")
        
        uploaded_file = st.file_uploader(
            "Upload Company Data",
            type=["json", "csv", "txt", "tsv"],
            help="Upload structured company data for privacy-first analysis"
        )
        
        if uploaded_file:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"{uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
            with col2:
                if st.button("Process File", type="primary", use_container_width=True):
                    with st.spinner("Processing with Privacy Mode..."):
                        try:
                            # Import Privacy components
                            import tempfile
                            import asyncio
                            from engine.privacy_ingestor import PrivacyIngestor
                            from engine.privacy_graph_builder import PrivacyGraphBuilder
                            from db.neo4j_db import Neo4jDatabase
                            
                            # Save uploaded file temporarily
                            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_file_path = tmp_file.name
                            
                            # Initialize Neo4j if configured
                            neo4j_db = None
                            if NEO4J_URI and NEO4J_PASSWORD:
                                try:
                                    neo4j_db = Neo4jDatabase(
                                        uri=NEO4J_URI,
                                        username=NEO4J_USER,
                                        password=NEO4J_PASSWORD
                                    )
                                except Exception as e:
                                    st.warning(f"Neo4j connection failed: {e}. Continuing without graph storage.")
                            
                            # Initialize components
                            ingestor = PrivacyIngestor()
                            builder = PrivacyGraphBuilder(neo4j_db=neo4j_db)
                            
                            # Create progress indicators
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            # Process file
                            status_text.text("Reading file...")
                            chunks = list(ingestor.ingest_file(tmp_file_path))
                            total_chunks = len(chunks)
                            
                            status_text.text(f"Processing {total_chunks} chunks...")
                            
                            # Build graph asynchronously
                            async def build_graph():
                                stats = {"processed": 0}
                                
                                for i, chunk in enumerate(chunks):
                                    await builder.process_chunk(chunk)
                                    stats["processed"] = i + 1
                                    progress_bar.progress((i + 1) / total_chunks)
                                    status_text.text(f"Processed {i + 1}/{total_chunks} chunks")
                                
                                return builder.stats
                            
                            # Run async function
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            stats = loop.run_until_complete(build_graph())
                            loop.close()
                            
                            # Show results
                            progress_bar.progress(1.0)
                            status_text.text("Complete!")
                            
                            st.success("File processed successfully!")
                            st.json({
                                "chunks_processed": stats["chunks_processed"],
                                "entities_extracted": stats["entities_extracted"],
                                "relationships_extracted": stats["relationships_extracted"],
                                "queries_executed": stats["queries_executed"],
                                "errors": stats["errors"]
                            })
                            
                            # Cleanup
                            import os
                            os.unlink(tmp_file_path)
                            
                        except Exception as e:
                            st.error(f"Processing error: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
    
    elif input_method == "PDF Upload":
        uploaded_file = st.file_uploader(
            "Upload PDF document",
            type=["pdf"],
            help="Upload a PDF file to extract and index its content"
        )
        
        if uploaded_file:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"{uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
            with col2:
                if st.button("Process PDF", type="primary", use_container_width=True):
                    with st.spinner("Processing PDF document..."):
                        try:
                            # 파일을 임시로 저장
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_path = tmp_file.name
                            
                            # utils.py에서 PDF 텍스트 추출
                            from utils import extract_text_from_pdf
                            extracted_text = extract_text_from_pdf(tmp_path)
                            
                            # 임시 파일 삭제
                            os.unlink(tmp_path)
                            
                            if not extracted_text or not extracted_text.strip():
                                st.error("PDF에서 텍스트를 추출할 수 없습니다. OCR이 필요한 이미지 기반 PDF일 수 있습니다.")
                            else:
                                # 인덱싱 요청
                                if USE_DIRECT_ENGINE:
                                    # Streamlit Cloud: 직접 엔진 사용
                                    engine = get_direct_engine()
                                    if engine is None:
                                        st.error("GraphRAG 엔진을 초기화할 수 없습니다.")
                                    else:
                                        try:
                                            import asyncio
                                            loop = asyncio.new_event_loop()
                                            asyncio.set_event_loop(loop)
                                            loop.run_until_complete(engine.ainsert(extracted_text))
                                            loop.close()
                                            
                                            # 데이터 소스 저장
                                            data_sources = load_data_sources()
                                            data_sources["pdf"].append({
                                                "filename": uploaded_file.name,
                                                "size": uploaded_file.size,
                                                "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                                            })
                                            save_data_sources(data_sources)
                                            
                                            st.success(f"{uploaded_file.name} successfully indexed!")
                                        except Exception as e:
                                            st.error(f"인덱싱 실패: {str(e)}")
                                else:
                                    # 로컬: FastAPI 서버 사용
                                    response = requests.post(
                                        f"{API_BASE_URL}/insert",
                                        json={"text": extracted_text},
                                        timeout=300
                                    )
                                    
                                    if response.status_code == 200:
                                        # 데이터 소스 저장
                                        data_sources = load_data_sources()
                                        data_sources["pdf"].append({
                                            "filename": uploaded_file.name,
                                            "size": uploaded_file.size,
                                            "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                                        })
                                        save_data_sources(data_sources)
                                        
                                        st.success(f"{uploaded_file.name} successfully indexed!")
                                    else:
                                        st.error(f"Indexing failed: {response.status_code} - {response.text}")
                        except Exception as e:
                            st.error(f"Error processing PDF: {str(e)}")
    
    else:  # URL Crawling
        url_input = st.text_input(
            "Enter URL to crawl",
            placeholder="https://example.com"
        )
        
        if st.button("Crawl & Index", type="primary"):
            if url_input.strip():
                st.info("URL crawling feature coming soon!")
            else:
                st.warning("Please enter a URL.")

# Tab 3: Data Sources
with tab3:
    st.markdown("### Data Sources")
    
    data_sources = load_data_sources()
    
    # PDF Sources
    st.markdown("#### PDF Documents")
    if data_sources["pdf"]:
        for idx, source in enumerate(data_sources["pdf"]):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(f"{source['filename']}")
            with col2:
                st.text(f"Size: {source['size'] / 1024:.1f} KB | Indexed: {source['indexed_at']}")
            with col3:
                if st.button("Delete", key=f"del_pdf_{idx}"):
                    if delete_data_source("pdf", idx):
                        st.rerun()
    else:
        st.info("No PDF documents indexed yet.")
    
    st.markdown("---")
    
    # Text Sources
    st.markdown("#### 📝 Text Inputs")
    if data_sources["text"]:
        for idx, source in enumerate(data_sources["text"]):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(f"📝 {source['preview']}")
            with col2:
                st.text(f"Length: {source['length']} chars | Indexed: {source['indexed_at']}")
            with col3:
                if st.button("Delete", key=f"del_text_{idx}"):
                    if delete_data_source("text", idx):
                        st.rerun()
    else:
        st.info("No text inputs indexed yet.")
    
    st.markdown("---")
    
    # URL Sources
    st.markdown("#### URL Sources")
    if data_sources["url"]:
        for idx, source in enumerate(data_sources["url"]):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(f"{source['url']}")
            with col2:
                st.text(f"Indexed: {source['indexed_at']}")
            with col3:
                if st.button("Delete", key=f"del_url_{idx}"):
                    if delete_data_source("url", idx):
                        st.rerun()
    else:
        st.info("No URLs indexed yet.")


# Tab 4: Domain Analysis
with tab4:
    st.markdown("### 🏗️ Domain Analysis")
    st.markdown("금융 도메인 특화 분석: Event-Actor-Asset-Factor-Region 관계 탐색")
    
    # 분석 유형 선택
    analysis_type = st.selectbox(
        "분석 유형",
        ["Event 인과관계", "Actor 영향력", "Region 이벤트", "Asset 요인 분석"],
        help="분석하고 싶은 도메인 관계 유형을 선택하세요"
    )
    
    # Event 인과관계 분석
    if analysis_type == "Event 인과관계":
        st.markdown("#### Event → Factor → Asset 인과관계 체인")
        
        event_name = st.text_input(
            "Event 이름",
            placeholder="예: Fed 금리 인상, SVB 파산, 중국 부동산 위기",
            help="분석하고 싶은 금융 이벤트 이름을 입력하세요"
        )
        
        if st.button("분석", key="analyze_event"):
            if not event_name:
                st.warning("Event 이름을 입력해주세요.")
            else:
                with st.spinner(f"'{event_name}' 인과관계 분석 중..."):
                    try:
                        response = requests.get(
                            f"{API_BASE_URL}/domain/event/{event_name}",
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            impact_chain = result.get("impact_chain", [])
                            
                            if impact_chain:
                                st.success(f"✅ {len(impact_chain)}개의 인과관계를 발견했습니다!")
                                
                                for idx, chain in enumerate(impact_chain, 1):
                                    with st.expander(f"인과관계 {idx}: {chain['factor']['name']} → {chain['asset']['name']}", expanded=True):
                                        col1, col2, col3 = st.columns(3)
                                        
                                        with col1:
                                            st.markdown("**Event**")
                                            st.write(f"이름: {chain['event']['name']}")
                                            st.write(f"날짜: {chain['event'].get('date', 'N/A')}")
                                            st.write(f"영향 수준: {chain['event'].get('impact_level', 'N/A')}")
                                        
                                        with col2:
                                            st.markdown("**Factor**")
                                            st.write(f"이름: {chain['factor']['name']}")
                                            st.write(f"타입: {chain['factor']['type']}")
                                        
                                        with col3:
                                            st.markdown("**Asset**")
                                            st.write(f"이름: {chain['asset']['name']}")
                                            st.write(f"타입: {chain['asset']['type']}")
                                        
                                        st.markdown("**영향 분석**")
                                        direction = chain['impact']['direction']
                                        magnitude = chain['impact']['magnitude']
                                        confidence = chain['impact']['confidence']
                                        
                                        direction_emoji = "📈" if direction == "Positive" else "📉"
                                        st.write(f"{direction_emoji} 방향: {direction}")
                                        st.write(f"📊 크기: {magnitude:.2f}")
                                        st.write(f"🎯 신뢰도: {confidence:.2f}")
                            else:
                                st.info(f"'{event_name}'에 대한 인과관계를 찾을 수 없습니다.")
                        else:
                            st.error(f"API 에러: {response.status_code}")
                    
                    except Exception as e:
                        st.error(f"분석 중 에러 발생: {str(e)}")
    
    # Actor 영향력 분석
    elif analysis_type == "Actor 영향력":
        st.markdown("#### Actor가 관여한 Event와 영향 분석")
        
        actor_name = st.text_input(
            "Actor 이름",
            placeholder="예: Federal Reserve, 중국 정부, BlackRock",
            help="분석하고 싶은 주체(기관, 정부, 기업) 이름을 입력하세요"
        )
        
        if st.button("분석", key="analyze_actor"):
            if not actor_name:
                st.warning("Actor 이름을 입력해주세요.")
            else:
                with st.spinner(f"'{actor_name}' 영향력 분석 중..."):
                    try:
                        response = requests.get(
                            f"{API_BASE_URL}/domain/actor/{actor_name}",
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            influence_data = result.get("influence", [])
                            
                            if influence_data:
                                st.success(f"✅ {len(influence_data)}개의 영향 관계를 발견했습니다!")
                                
                                for idx, data in enumerate(influence_data, 1):
                                    with st.expander(f"영향 {idx}: {data['event']['name']}", expanded=True):
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            st.markdown("**Actor 정보**")
                                            st.write(f"이름: {data['actor']['name']}")
                                            st.write(f"타입: {data['actor']['type']}")
                                            st.write(f"역할: {data['actor'].get('role', 'N/A')}")
                                            st.write(f"영향력: {data['actor'].get('influence_level', 'N/A')}")
                                            
                                            st.markdown("**Event 정보**")
                                            st.write(f"이름: {data['event']['name']}")
                                            st.write(f"날짜: {data['event'].get('date', 'N/A')}")
                                        
                                        with col2:
                                            st.markdown("**Factor → Asset 영향**")
                                            st.write(f"Factor: {data['factor']['name']} ({data['factor']['type']})")
                                            st.write(f"Asset: {data['asset']['name']} ({data['asset']['type']})")
                                            
                                            direction = data['impact']['direction']
                                            magnitude = data['impact']['magnitude']
                                            direction_emoji = "📈" if direction == "Positive" else "📉"
                                            st.write(f"{direction_emoji} 영향: {direction} (크기: {magnitude:.2f})")
                            else:
                                st.info(f"'{actor_name}'에 대한 영향 관계를 찾을 수 없습니다.")
                        else:
                            st.error(f"API 에러: {response.status_code}")
                    
                    except Exception as e:
                        st.error(f"분석 중 에러 발생: {str(e)}")
    
    # Region 이벤트 분석
    elif analysis_type == "Region 이벤트":
        st.markdown("#### 특정 지역의 Event와 영향받은 Asset")
        
        region_name = st.text_input(
            "Region 이름",
            placeholder="예: 미국, 중국, 아시아, 신흥시장",
            help="분석하고 싶은 지역 이름을 입력하세요"
        )
        
        if st.button("분석", key="analyze_region"):
            if not region_name:
                st.warning("Region 이름을 입력해주세요.")
            else:
                with st.spinner(f"'{region_name}' 이벤트 분석 중..."):
                    try:
                        response = requests.get(
                            f"{API_BASE_URL}/domain/region/{region_name}",
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            regional_events = result.get("events", [])
                            
                            if regional_events:
                                st.success(f"✅ {len(regional_events)}개의 지역 이벤트를 발견했습니다!")
                                
                                for idx, event in enumerate(regional_events, 1):
                                    with st.expander(f"이벤트 {idx}: {event['event']['name']}", expanded=True):
                                        col1, col2, col3 = st.columns(3)
                                        
                                        with col1:
                                            st.markdown("**Event**")
                                            st.write(f"이름: {event['event']['name']}")
                                            st.write(f"날짜: {event['event'].get('date', 'N/A')}")
                                            st.write(f"영향 수준: {event['event'].get('impact_level', 'N/A')}")
                                        
                                        with col2:
                                            st.markdown("**Region**")
                                            st.write(f"이름: {event['region']['name']}")
                                            st.write(f"타입: {event['region']['type']}")
                                            st.write(f"영향 범위: {event['region'].get('impact_scope', 'N/A')}")
                                        
                                        with col3:
                                            st.markdown("**Factor → Asset**")
                                            st.write(f"Factor: {event['factor']['name']}")
                                            st.write(f"Asset: {event['asset']['name']}")
                                            
                                            direction = event['impact']['direction']
                                            magnitude = event['impact']['magnitude']
                                            direction_emoji = "📈" if direction == "Positive" else "📉"
                                            st.write(f"{direction_emoji} {direction} ({magnitude:.2f})")
                            else:
                                st.info(f"'{region_name}'에 대한 이벤트를 찾을 수 없습니다.")
                        else:
                            st.error(f"API 에러: {response.status_code}")
                    
                    except Exception as e:
                        st.error(f"분석 중 에러 발생: {str(e)}")
    
    # Asset 요인 분석
    elif analysis_type == "Asset 요인 분석":
        st.markdown("#### Asset에 영향을 주는 Factor 분석")
        
        asset_name = st.text_input(
            "Asset 이름",
            placeholder="예: 금, 미국 부동산, NVDA, 국채",
            help="분석하고 싶은 자산 이름을 입력하세요"
        )
        
        if st.button("분석", key="analyze_asset"):
            if not asset_name:
                st.warning("Asset 이름을 입력해주세요.")
            else:
                with st.spinner(f"'{asset_name}' 요인 분석 중..."):
                    try:
                        response = requests.get(
                            f"{API_BASE_URL}/domain/asset/{asset_name}",
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            factors = result.get("factors", [])
                            
                            if factors:
                                st.success(f"✅ {len(factors)}개의 영향 요인을 발견했습니다!")
                                
                                for idx, factor_data in enumerate(factors, 1):
                                    with st.expander(f"요인 {idx}: {factor_data['factor']['name']}", expanded=True):
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            st.markdown("**Factor 정보**")
                                            st.write(f"이름: {factor_data['factor']['name']}")
                                            st.write(f"타입: {factor_data['factor']['type']}")
                                            value = factor_data['factor'].get('value')
                                            if value is not None:
                                                st.write(f"값: {value}")
                                        
                                        with col2:
                                            st.markdown("**영향 분석**")
                                            direction = factor_data['impact']['direction']
                                            magnitude = factor_data['impact']['magnitude']
                                            confidence = factor_data['impact']['confidence']
                                            
                                            direction_emoji = "📈" if direction == "Positive" else "📉"
                                            st.write(f"{direction_emoji} 방향: {direction}")
                                            st.write(f"📊 크기: {magnitude:.2f}")
                                            st.write(f"🎯 신뢰도: {confidence:.2f}")
                                        
                                        # 트리거 이벤트
                                        triggering_events = factor_data.get('triggering_events', [])
                                        if triggering_events:
                                            st.markdown("**트리거 이벤트**")
                                            st.write(", ".join(triggering_events))
                            else:
                                st.info(f"'{asset_name}'에 대한 영향 요인을 찾을 수 없습니다.")
                        else:
                            st.error(f"API 에러: {response.status_code}")
                    
                    except Exception as e:
                        st.error(f"분석 중 에러 발생: {str(e)}")
    
    st.markdown("---")
    
    # 도메인 스키마 초기화 버튼
    st.markdown("### 도메인 스키마 관리")
    
    if st.button("🔧 도메인 스키마 초기화", help="Neo4j에 도메인 스키마 Constraint 및 Index 생성"):
        with st.spinner("도메인 스키마 초기화 중..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/domain/schema/init",
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        st.success(f"✅ 도메인 스키마 초기화 완료!")
                        st.write(f"Constraints: {result.get('constraints', 0)}개")
                        st.write(f"Indexes: {result.get('indexes', 0)}개")
                    else:
                        st.error(f"초기화 실패: {result.get('message', 'Unknown error')}")
                else:
                    st.error(f"API 에러: {response.status_code}")
            
            except Exception as e:
                st.error(f"초기화 중 에러 발생: {str(e)}")
