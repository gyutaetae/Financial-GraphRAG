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

# 환경 변수 읽기
try:
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
except:
    pass

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
    page_icon="📊",
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
            tooltip_html = f'''
            <a href="#source-{cite_num}" class="citation">
                [{cite_num}]
                <div class="citation-tooltip">
                    <div class="tooltip-header">{display_name}</div>
                    <div class="tooltip-content">{excerpt}...</div>
                    <div class="tooltip-meta">{tooltip_meta}</div>
                </div>
            </a>
            '''
            return tooltip_html
        return match.group(0)
    
    # Citation을 HTML로 변환
    html_answer = re.sub(citation_pattern, replace_citation, answer)
    
    # References 섹션 생성
    references_html = '<div class="references"><h3>📚 References</h3>'
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
        
        references_html += f'''
        <div class="reference-item" id="source-{cite_id}">
            <span class="reference-number">[{cite_id}]</span>
            <span class="reference-file">{display_name}</span> ({meta_info})
            <div class="reference-excerpt">"{excerpt}..."</div>
        </div>
        '''
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
    st.markdown("### 📚 Source Details")
    
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
    r = requests.post(f"{api_base_url}/query", json=payload, timeout=120)
    if r.status_code == 200:
        return r.json()
    return {"_error": f"Error {r.status_code}: {r.text}"}

# System Status Bar (Top)
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.markdown("# 📊 VIK AI: Executive Intelligence")
    st.markdown("*Powered by Hybrid GraphRAG*")

with col2:
    server_connected = cached_health(API_BASE_URL)
    
    # Streamlit Cloud 모드일 때는 다른 메시지 표시
    if USE_DIRECT_ENGINE:
        status_text = "Direct Engine Mode"
        status_color = "#28a745"
    else:
        status_text = "Backend Connected" if server_connected else "Backend Disconnected"
        status_color = "#28a745" if server_connected else "#dc3545"
    
    status_html = f"""
    <div style="text-align: right; padding: 10px;">
        <span style="color: {status_color}; font-size: 12px;">
            ● {status_text}
        </span>
    </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)

with col3:
    if st.button("🔄 Refresh", type="secondary"):
        st.rerun()

st.markdown("---")

# Main Tabs
tab1, tab2, tab3 = st.tabs(["💬 Query Interface", "📤 Data Ingestion", "📊 Data Sources"])

# Tab 1: Query Interface
with tab1:
    st.markdown("### Query Interface")
    
    # Advanced Settings Expander
    with st.expander("⚙️ Advanced Settings", expanded=False):
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
            "🌐 Enable Web Search",
            value=False,
            help="Check this to allow AI to search the web for real-time information. Otherwise, it will ONLY use your uploaded PDF documents."
        )
        
        if enable_web_search:
            st.warning("⚠️ Web search enabled: AI may search the web for LATEST/TODAY information if needed.")
        else:
            st.success("✅ Document-only mode: AI will answer ONLY from your uploaded PDFs.")
        
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
        st.markdown("**📊 Parameter Guide:**")
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
    
    st.session_state.temperature = temperature
    st.session_state.top_k = top_k
    st.session_state.enable_web_search = enable_web_search
    
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
                    # Citation과 References가 포함된 보고서 형식
                    report_html = render_report_with_citations(message["content"], sources)
                    st.markdown(report_html, unsafe_allow_html=True)
                    
                    # Popover로 추가 상세 정보 제공 (선택사항)
                    with st.expander(f"📎 View {len(sources)} Source(s) in Detail", expanded=False):
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
                request_data = {
                    "question": prompt,
                    "mode": "api",
                    "temperature": st.session_state.get("temperature", 0.2),
                    "top_k": st.session_state.get("top_k", 30),
                    "search_type": search_type,
                    "enable_web_search": st.session_state.get("enable_web_search", False)
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
                    
                    # Add assistant response to chat history with sources
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "source_type": source_type,
                        "mode": mode,
                        "validation": validation,
                        "evidence": evidence
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
    
    input_method = st.radio(
        "Select input method",
        options=["PDF Upload", "URL Crawling"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if input_method == "PDF Upload":
        uploaded_file = st.file_uploader(
            "Upload PDF document",
            type=["pdf"],
            help="Upload a PDF file to extract and index its content"
        )
        
        if uploaded_file:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"📄 {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
            with col2:
                if st.button("🚀 Process PDF", type="primary", use_container_width=True):
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
                                            
                                            st.success(f"✅ {uploaded_file.name} successfully indexed!")
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
                                        
                                        st.success(f"✅ {uploaded_file.name} successfully indexed!")
                                    else:
                                        st.error(f"Indexing failed: {response.status_code} - {response.text}")
                        except Exception as e:
                            st.error(f"Error processing PDF: {str(e)}")
    
    else:  # URL Crawling
        url_input = st.text_input(
            "Enter URL to crawl",
            placeholder="https://example.com"
        )
        
        if st.button("🚀 Crawl & Index", type="primary"):
            if url_input.strip():
                st.info("URL crawling feature coming soon!")
            else:
                st.warning("Please enter a URL.")

# Tab 3: Data Sources
with tab3:
    st.markdown("### Data Sources")
    
    data_sources = load_data_sources()
    
    # PDF Sources
    st.markdown("#### 📄 PDF Documents")
    if data_sources["pdf"]:
        for idx, source in enumerate(data_sources["pdf"]):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(f"📄 {source['filename']}")
            with col2:
                st.text(f"Size: {source['size'] / 1024:.1f} KB | Indexed: {source['indexed_at']}")
            with col3:
                if st.button("🗑️", key=f"del_pdf_{idx}"):
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
                if st.button("🗑️", key=f"del_text_{idx}"):
                    if delete_data_source("text", idx):
                        st.rerun()
    else:
        st.info("No text inputs indexed yet.")
    
    st.markdown("---")
    
    # URL Sources
    st.markdown("#### 🌐 URL Sources")
    if data_sources["url"]:
        for idx, source in enumerate(data_sources["url"]):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(f"🌐 {source['url']}")
            with col2:
                st.text(f"Indexed: {source['indexed_at']}")
            with col3:
                if st.button("🗑️", key=f"del_url_{idx}"):
                    if delete_data_source("url", idx):
                        st.rerun()
    else:
        st.info("No URLs indexed yet.")
