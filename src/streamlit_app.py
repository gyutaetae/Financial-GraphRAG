import streamlit as st
import requests
import sys
import os
import streamlit.components.v1 as components
import time
import json
from datetime import datetime
import re
from typing import List, Dict

# .env 파일 읽기
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 현재 파일의 폴더 경로를 추가해요!
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 페이지 설정 - Executive Dashboard
st.set_page_config(
    page_title="Financial Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Perplexity 스타일 CSS
st.markdown("""
<style>
/* 전체 앱 스타일 */
.stApp {
    background-color: #fafafa;
}

/* 보고서 컨테이너 */
.report-container {
    background: white;
    padding: 2.5rem;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin: 1rem 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
    line-height: 1.7;
}

/* 보고서 제목 */
.report-container h2 {
    color: #1a1a1a;
    font-size: 1.5rem;
    font-weight: 600;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    border-bottom: 2px solid #f0f0f0;
    padding-bottom: 0.5rem;
}

/* Citation 스타일 */
.citation {
    display: inline-block;
    color: #0066cc;
    background: #e6f2ff;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-size: 0.85em;
    font-weight: 600;
    margin: 0 0.1rem;
    cursor: help;
    text-decoration: none;
    transition: all 0.2s;
    position: relative;
}

.citation:hover {
    background: #0066cc;
    color: white;
    transform: translateY(-1px);
}

/* Citation Tooltip */
.citation-tooltip {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    background-color: #1a1a1a;
    color: #fff;
    text-align: left;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    width: 350px;
    max-width: 90vw;
    font-size: 0.875rem;
    font-weight: normal;
    z-index: 1000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    transition: opacity 0.2s, visibility 0.2s;
    pointer-events: none;
}

.citation-tooltip::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: #1a1a1a;
}

.citation:hover .citation-tooltip {
    visibility: visible;
    opacity: 1;
}

.citation-tooltip-title {
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #fff;
    border-bottom: 1px solid #444;
    padding-bottom: 0.5rem;
}

.citation-tooltip-content {
    color: #e0e0e0;
    line-height: 1.5;
    max-height: 200px;
    overflow-y: auto;
}

.citation-tooltip-chunk {
    font-size: 0.8em;
    color: #999;
    margin-top: 0.5rem;
}

/* References 섹션 */
.references {
    margin-top: 2.5rem;
    padding-top: 1.5rem;
    border-top: 2px solid #e0e0e0;
}

.references h4 {
    color: #333;
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 1rem;
}

.references ol {
    padding-left: 1.5rem;
}

.references li {
    margin-bottom: 1rem;
    line-height: 1.6;
}

.references li strong {
    color: #0066cc;
}

.references li em {
    color: #666;
    font-size: 0.9em;
}

/* Executive Summary 아이콘 */
.report-container p:has(> strong:first-child) {
    background: #f8f9fa;
    padding: 1rem;
    border-left: 4px solid #0066cc;
    border-radius: 4px;
}

/* Key Findings 리스트 */
.report-container ul {
    list-style: none;
    padding-left: 0;
}

.report-container ul li {
    padding-left: 1.5rem;
    margin-bottom: 0.75rem;
    position: relative;
}

.report-container ul li:before {
    content: "▸";
    position: absolute;
    left: 0;
    color: #0066cc;
    font-weight: bold;
}

/* 차트 메시지 스타일 개선 */
.stChatMessage {
    background: white !important;
    border-radius: 12px;
    padding: 1rem;
    margin: 0.5rem 0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

/* 사용자 메시지 */
[data-testid="stChatMessageContent"][data-test-user="true"] {
    background: #f0f7ff;
    border-left: 3px solid #0066cc;
}

/* 코드 블록 */
.report-container code {
    background: #f5f5f5;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    font-size: 0.9em;
}

/* Popover 스타일 (Streamlit native) */
[data-baseweb="popover"] {
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
</style>
""", unsafe_allow_html=True)

# 데이터 소스 관리 파일 경로
DATA_SOURCES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_sources.json")

# 데이터 소스 로드 함수
def load_data_sources():
    if os.path.exists(DATA_SOURCES_FILE):
        with open(DATA_SOURCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"pdfs": [], "urls": [], "texts": []}

# 데이터 소스 저장 함수
def save_data_sources(data_sources):
    with open(DATA_SOURCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_sources, f, ensure_ascii=False, indent=2)

# 데이터 소스 추가 함수
def add_data_source(source_type, name, content_preview=""):
    data_sources = load_data_sources()
    source = {
        "name": name,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "content_preview": content_preview[:100] + "..." if len(content_preview) > 100 else content_preview
    }
    data_sources[source_type].append(source)
    save_data_sources(data_sources)


# Citation 렌더링 함수
def render_report_with_citations(answer: str, sources: List[Dict]) -> str:
    """
    답변 텍스트에 Citation을 인터랙티브하게 렌더링
    
    Args:
        answer: LLM 답변 (마크다운 형식)
        sources: 출처 리스트 [{"id": 1, "file": "...", "excerpt": "...", "chunk_id": "..."}, ...]
    
    Returns:
        HTML 형식의 렌더링된 보고서
    """
    if not sources:
        # 출처가 없으면 그냥 마크다운 그대로 반환
        return f"<div class='report-container'>{answer}</div>"
    
    # Citation 패턴 찾기: [1], [2], [1,2], [1][2] 등
    citation_pattern = r'\[(\d+(?:\s*,\s*\d+)*)\]'
    
    def replace_citation(match):
        citations = match.group(1)
        citation_nums = [int(n.strip()) for n in citations.split(',')]
        
        # 여러 citation을 span으로 변환
        html_citations = []
        for num in citation_nums:
            # 해당 번호의 소스 찾기
            source = next((s for s in sources if s['id'] == num), None)
            if source:
                file_name = source.get('file', 'Unknown source')
                chunk_id = source.get('chunk_id', 'N/A')
                excerpt = source.get('excerpt', '')
                # HTML 특수문자 이스케이프
                import html
                file_name_escaped = html.escape(file_name)
                excerpt_escaped = html.escape(excerpt[:200] + ('...' if len(excerpt) > 200 else ''))
                chunk_id_escaped = html.escape(str(chunk_id))
                
                tooltip_html = f"""
                <div class="citation-tooltip">
                    <div class="citation-tooltip-title">{file_name_escaped}</div>
                    <div class="citation-tooltip-content">{excerpt_escaped}</div>
                    <div class="citation-tooltip-chunk">Chunk ID: {chunk_id_escaped}</div>
                </div>
                """
                html_citations.append(
                    f'<span class="citation">{tooltip_html}[{num}]</span>'
                )
            else:
                html_citations.append(f'<span class="citation">[{num}]</span>')
        
        return ''.join(html_citations)
    
    # Citation 교체
    answer_with_citations = re.sub(citation_pattern, replace_citation, answer)
    
    # References 섹션 생성
    references_html = "<div class='references'><h4>References</h4><ol>"
    for source in sources:
        file_name = source.get('file', 'Unknown')
        chunk_id = source.get('chunk_id', 'N/A')
        excerpt = source.get('excerpt', '')
        url = source.get('url', '')
        
        # URL이 있으면 링크로 표시
        if url and url.startswith('http'):
            references_html += f"<li><strong><a href='{url}' target='_blank'>{file_name}</a></strong><br>"
        else:
            references_html += f"<li><strong>{file_name}</strong> (Chunk: {chunk_id})<br>"
        
        references_html += f"<em>{excerpt[:250]}...</em></li>"
    
    references_html += "</ol></div>"
    
    # 전체 보고서 HTML
    report_html = f"""
    <div class='report-container'>
        {answer_with_citations}
        {references_html}
    </div>
    """
    
    return report_html


def render_citations_with_popover(sources: List[Dict]):
    """
    Streamlit popover를 사용하여 citation 클릭 시 출처 정보 표시
    
    Args:
        sources: 출처 리스트
    """
    if not sources:
        return
    
    st.markdown("---")
    st.markdown("### 📚 References")
    
    # 각 출처를 expander 또는 popover로 표시
    cols = st.columns(min(len(sources), 3))
    for idx, source in enumerate(sources):
        col_idx = idx % 3
        with cols[col_idx]:
            with st.popover(f"[{source['id']}] {source.get('file', 'Source')[:30]}...", use_container_width=True):
                st.caption(f"**File**: {source.get('file', 'Unknown')}")
                st.caption(f"**Chunk ID**: {source.get('chunk_id', 'N/A')}")
                
                if source.get('url'):
                    st.caption(f"**URL**: [{source['url']}]({source['url']})")
                
                st.text_area(
                    "Excerpt",
                    value=source.get('excerpt', '')[:400],
                    height=150,
                    disabled=True,
                    key=f"excerpt_{source['id']}"
                )

# 데이터 소스 삭제 함수
def delete_data_source(source_type, index):
    data_sources = load_data_sources()
    if 0 <= index < len(data_sources[source_type]):
        del data_sources[source_type][index]
        save_data_sources(data_sources)
        return True
    return False

# Executive Header
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f9fafb;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .status-active {
        background: #d1fae5;
        color: #065f46;
    }
    .status-error {
        background: #fee2e2;
        color: #991b1b;
    }
</style>
<div class="main-header">Financial Intelligence Platform</div>
<div class="sub-header">Knowledge Graph Analysis & Insights</div>
""", unsafe_allow_html=True)

# API 엔드포인트
API_BASE_URL = "http://127.0.0.1:8000"

# System Status Bar (Top)
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    # Server status check
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        server_connected = response.status_code == 200
    except:
        server_connected = False
    
    status_html = f"""
    <span class="status-badge {'status-active' if server_connected else 'status-error'}">
        {'● SYSTEM ACTIVE' if server_connected else '● SYSTEM OFFLINE'}
    </span>
    """
    st.markdown(status_html, unsafe_allow_html=True)

with col2:
    # Graph stats
    if server_connected:
        try:
            response = requests.get(f"{API_BASE_URL}/graph_stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                st.metric("Nodes", f"{stats.get('nodes', 0):,}", label_visibility="visible")
        except:
            st.metric("Nodes", "N/A")
    else:
        st.metric("Nodes", "N/A")

with col3:
    if server_connected:
        try:
            response = requests.get(f"{API_BASE_URL}/graph_stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                st.metric("Edges", f"{stats.get('edges', 0):,}", label_visibility="visible")
        except:
            st.metric("Edges", "N/A")
    else:
        st.metric("Edges", "N/A")

with col4:
    query_mode = st.selectbox(
        "Mode",
        options=["api", "local"],
        format_func=lambda x: "Cloud API" if x == "api" else "Local Model",
        label_visibility="visible"
    )

st.divider()

# Main Navigation
tab1, tab2, tab3, tab4 = st.tabs(["Query", "Data Ingestion", "Data Sources", "Graph Visualization"])

# Tab 1: Query Interface
with tab1:
    st.markdown("### Query Interface")
    
    # Advanced Settings Expander
    with st.expander("⚙️ Advanced Settings", expanded=False):
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
    
    st.session_state.temperature = temperature
    st.session_state.top_k = top_k
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Chat container with custom styling
    st.markdown("""
    <style>
        .chat-container {
            max-height: 500px;
            overflow-y: auto;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .user-message {
            background: #e3f2fd;
            padding: 1rem;
            border-radius: 12px;
            margin: 0.5rem 0 0.5rem auto;
            max-width: 70%;
            text-align: right;
        }
        .assistant-message {
            background: #f5f5f5;
            padding: 1rem;
            border-radius: 12px;
            margin: 0.5rem auto 0.5rem 0;
            max-width: 70%;
            text-align: left;
        }
        .message-mode {
            font-size: 0.75rem;
            color: #666;
            margin-top: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Display chat history with custom styling
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
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
                
                if sources:
                    # Citation과 References가 포함된 보고서 형식
                    report_html = render_report_with_citations(message["content"], sources)
                    st.markdown(report_html, unsafe_allow_html=True)
                    
                    # Popover로 추가 상세 정보 제공 (선택사항)
                    with st.expander(f"📎 View {len(sources)} Source(s) in Detail", expanded=False):
                        render_citations_with_popover(sources)
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
                request_data = {
                    "question": prompt,
                    "mode": query_mode,
                    "temperature": st.session_state.get("temperature", 0.2),
                    "top_k": st.session_state.get("top_k", 30)
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/query",
                    json=request_data,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("answer", "No response generated.")
                    sources = result.get("sources", [])
                    source_type = result.get("source", "UNKNOWN")
                    mode = result.get('mode', 'unknown').upper()
                    
                    # Add assistant response to chat history with sources
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "source_type": source_type,
                        "mode": mode
                    })
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
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
        options=["PDF Upload", "Text Input", "URL Crawling"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if input_method == "PDF Upload":
        uploaded_file = st.file_uploader(
            "Upload PDF document",
            type=["pdf"],
            key="pdf_uploader"
        )
        
        if st.button("Process PDF", type="primary", use_container_width=True):
            if not uploaded_file:
                st.warning("Please upload a PDF file.")
            else:
                progress_placeholder = st.empty()
                status_placeholder = st.empty()
                
                try:
                    # Step 1: Save file
                    progress_placeholder.progress(0.1)
                    status_placeholder.info("Saving PDF file...")
                    
                    safe_filename = uploaded_file.name.replace(" ", "_") if uploaded_file.name else "uploaded.pdf"
                    temp_pdf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"temp_{safe_filename}")
                    
                    with open(temp_pdf_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Step 2: Extract text
                    progress_placeholder.progress(0.2)
                    status_placeholder.info(f"Extracting text from {safe_filename}...")
                    
                    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from utils import extract_text_from_pdf
                    text = extract_text_from_pdf(temp_pdf_path)
                    
                    if os.path.exists(temp_pdf_path):
                        os.remove(temp_pdf_path)
                    
                    # 텍스트 검증
                    if not text or not text.strip():
                        status_placeholder.error("PDF에서 텍스트를 추출할 수 없습니다. 이미지 기반 PDF이거나 암호화되어 있을 수 있습니다.")
                        progress_placeholder.empty()
                        st.stop()
                    
                    if len(text.strip()) < 50:
                        status_placeholder.warning(f"추출된 텍스트가 너무 짧습니다 ({len(text)} 문자). 계속 진행하시겠습니까?")
                    
                    status_placeholder.success(f"Extracted {len(text):,} characters")
                    
                    # Step 3: Reset graph
                    progress_placeholder.progress(0.3)
                    status_placeholder.info("Resetting graph...")
                    
                    try:
                        reset_response = requests.post(f"{API_BASE_URL}/reset", timeout=30)
                        if reset_response.status_code == 200:
                            status_placeholder.success("Graph reset complete")
                    except Exception as reset_error:
                        status_placeholder.warning(f"Graph reset skipped: {str(reset_error)}")
                    
                    # Step 4: Index
                    progress_placeholder.progress(0.4)
                    status_placeholder.info("Indexing document... (this may take several minutes)")
                    
                    response = requests.post(
                        f"{API_BASE_URL}/insert",
                        json={"text": text},
                        timeout=600  # 10분 타임아웃
                    )
                    
                    progress_placeholder.progress(1.0)
                    
                    if response.status_code == 200:
                        status_placeholder.success(f"PDF indexed successfully. ({len(text):,} characters)")
                        add_data_source("pdfs", safe_filename, text)
                        st.balloons()
                    else:
                        status_placeholder.error(f"Indexing failed: {response.status_code} - {response.text}")
                        
                except requests.exceptions.Timeout:
                    status_placeholder.error("Request timed out. The document may be too large or the server is busy.")
                except requests.exceptions.ConnectionError:
                    status_placeholder.error("Cannot connect to server. Please ensure the FastAPI server is running.")
                except Exception as e:
                    status_placeholder.error(f"Error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                finally:
                    if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                        os.remove(temp_pdf_path)
    
    elif input_method == "Text Input":
        text_input = st.text_area(
            "Enter text to index",
            placeholder="Example: NVIDIA reported revenue of $57.0 billion in Q3 2026...",
            height=200,
            key="text_input"
        )
        
        if st.button("Index Text", type="primary", use_container_width=True):
            if not text_input:
                st.warning("Please enter text to index.")
            else:
                with st.spinner("Indexing in progress..."):
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/insert",
                            json={"text": text_input},
                            timeout=300
                        )
                        
                        if response.status_code == 200:
                            st.success("Text indexed successfully.")
                            add_data_source("texts", "Text Input", text_input)
                        else:
                            st.error(f"Indexing failed: {response.status_code}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    elif input_method == "URL Crawling":
        url_input = st.text_input(
            "Enter URL to crawl",
            placeholder="Example: https://www.example.com/financial-report",
            key="url_input"
        )
        
        if st.button("Crawl URL", type="primary", use_container_width=True):
            if not url_input:
                st.warning("Please enter a URL.")
            else:
                with st.spinner("Crawling web page..."):
                    try:
                        from url import auto_researcher
                        result = auto_researcher(url_input)
                        
                        if result.get("status") == "success":
                            st.success("URL crawled and indexed successfully.")
                            add_data_source("urls", url_input, result.get("text", "")[:100])
                        else:
                            st.error(f"Crawling failed: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

# Tab 3: Data Sources
with tab3:
    st.markdown("### Data Sources")
    
    # Sub-tabs for Data Sources
    source_tab1, source_tab2 = st.tabs(["Indexed Data", "Neo4j Graph"])
    
    with source_tab1:
        data_sources = load_data_sources()
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("PDF Documents", len(data_sources["pdfs"]))
        with col2:
            st.metric("URLs", len(data_sources["urls"]))
        with col3:
            st.metric("Text Entries", len(data_sources["texts"]))
        
        st.markdown("---")
        
        # PDF list
        if data_sources["pdfs"]:
            st.markdown("**PDF Documents**")
            for idx, pdf in enumerate(data_sources["pdfs"]):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.text(pdf['name'])
                with col2:
                    st.caption(pdf['added_at'])
                with col3:
                    if st.button("Delete", key=f"delete_pdf_{idx}"):
                        delete_data_source("pdfs", idx)
                        st.rerun()
                with st.expander("Preview"):
                    st.text(pdf.get('content_preview', 'No preview'))
            st.markdown("---")
        
        # URL list
        if data_sources["urls"]:
            st.markdown("**URLs**")
            for idx, url in enumerate(data_sources["urls"]):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.text(url['name'])
                with col2:
                    st.caption(url['added_at'])
                with col3:
                    if st.button("Delete", key=f"delete_url_{idx}"):
                        delete_data_source("urls", idx)
                        st.rerun()
                with st.expander("Preview"):
                    st.text(url.get('content_preview', 'No preview'))
            st.markdown("---")
        
        # Text list
        if data_sources["texts"]:
            st.markdown("**Text Entries**")
            for idx, text in enumerate(data_sources["texts"]):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.text(text['name'])
                with col2:
                    st.caption(text['added_at'])
                with col3:
                    if st.button("Delete", key=f"delete_text_{idx}"):
                        delete_data_source("texts", idx)
                        st.rerun()
                with st.expander("Preview"):
                    st.text(text.get('content_preview', 'No preview'))
            st.markdown("---")
        
        # Clear all
        if st.button("Clear All Records", type="secondary"):
            save_data_sources({"pdfs": [], "urls": [], "texts": []})
            st.rerun()
    
    with source_tab2:
        st.markdown("### Neo4j Graph Visualization")
        
        # Neo4j connection info
        neo4j_uri = os.getenv("NEO4J_URI", "")
        neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        
        if not neo4j_uri or not neo4j_password:
            st.warning("⚠️ Neo4j connection not configured. Please set NEO4J_URI and NEO4J_PASSWORD in your .env file.")
            st.markdown("""
            **Setup Instructions:**
            1. Create a Neo4j AuraDB instance at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura)
            2. Copy your connection URI and credentials
            3. Add to `.env` file:
            ```
            NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
            NEO4J_USERNAME=neo4j
            NEO4J_PASSWORD=your-password
            ```
            """)
        else:
            st.success(f"✅ Connected to: {neo4j_uri}")
            
            # Quick Query Buttons
            st.markdown("#### Quick Queries")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("All Nodes & Edges", use_container_width=True):
                    st.session_state["selected_query"] = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100"
            with col2:
                if st.button("Show Entities", use_container_width=True):
                    st.session_state["selected_query"] = "MATCH (n:ENTITY) RETURN n LIMIT 100"
            with col3:
                if st.button("Show Communities", use_container_width=True):
                    st.session_state["selected_query"] = "MATCH (n:COMMUNITY) RETURN n LIMIT 50"
            with col4:
                if st.button("Graph Stats", use_container_width=True):
                    st.session_state["show_stats"] = True
            
            st.markdown("---")
            
            # Custom Query input
            default_query = st.session_state.get("selected_query", "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50")
            cypher_query = st.text_area(
                "Custom Cypher Query",
                value=default_query,
                height=100,
                help="Enter a Cypher query to visualize the graph"
            )
            
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                execute_button = st.button("🔍 Execute Query", type="primary", use_container_width=True)
            with col2:
                if st.button("📊 Show Database Stats", type="secondary", use_container_width=True):
                    st.session_state["show_stats"] = True
            with col3:
                if st.button("🗑️ Clear Results", type="secondary", use_container_width=True):
                    if "neo4j_results" in st.session_state:
                        del st.session_state["neo4j_results"]
                    if "show_stats" in st.session_state:
                        del st.session_state["show_stats"]
                    st.rerun()
            
            # Show Database Statistics
            if st.session_state.get("show_stats", False):
                st.markdown("---")
                st.markdown("#### 📊 Database Statistics")
                try:
                    from neo4j import GraphDatabase
                    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
                    
                    with driver.session() as session:
                        # Count nodes by label
                        node_counts = session.run("CALL db.labels() YIELD label RETURN label").value()
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            total_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                            st.metric("Total Nodes", f"{total_nodes:,}")
                        
                        with col2:
                            total_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
                            st.metric("Total Relationships", f"{total_rels:,}")
                        
                        with col3:
                            label_count = len(node_counts)
                            st.metric("Node Types", label_count)
                        
                        # Show breakdown by label
                        if node_counts:
                            st.markdown("**Nodes by Type:**")
                            for label in node_counts:
                                count = session.run(f"MATCH (n:{label}) RETURN count(n) as count").single()["count"]
                                st.text(f"  • {label}: {count:,}")
                    
                    driver.close()
                    st.session_state["show_stats"] = False
                    
                except Exception as e:
                    st.error(f"Failed to retrieve stats: {str(e)}")
                
                st.markdown("---")
            
            if execute_button:
                with st.spinner("Executing query..."):
                    try:
                        from neo4j import GraphDatabase
                        
                        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
                        
                        with driver.session() as session:
                            result = session.run(cypher_query)
                            records = list(result)
                            
                            if not records:
                                st.warning("Query returned no results.")
                            else:
                                st.success(f"Query returned {len(records)} records.")
                                
                                # Store results in session state
                                st.session_state["neo4j_results"] = records
                                
                                # Display results
                                st.markdown("#### Query Results")
                                
                                # Extract nodes and relationships
                                nodes = []
                                edges = []
                                node_ids = set()
                                
                                for record in records:
                                    for key in record.keys():
                                        value = record[key]
                                        
                                        # Check if it's a node
                                        if hasattr(value, 'labels') and hasattr(value, 'id'):
                                            node_id = value.id
                                            if node_id not in node_ids:
                                                node_ids.add(node_id)
                                                props = dict(value)
                                                label = list(value.labels)[0] if value.labels else "Node"
                                                name = props.get('name', props.get('id', f"Node {node_id}"))
                                                nodes.append({
                                                    "id": node_id,
                                                    "label": name,
                                                    "type": label,
                                                    "properties": props
                                                })
                                        
                                        # Check if it's a relationship
                                        elif hasattr(value, 'type') and hasattr(value, 'start_node') and hasattr(value, 'end_node'):
                                            props = dict(value)
                                            edges.append({
                                                "from": value.start_node.id,
                                                "to": value.end_node.id,
                                                "label": value.type,
                                                "properties": props
                                            })
                                
                                # Display statistics
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Nodes", len(nodes))
                                with col2:
                                    st.metric("Relationships", len(edges))
                                
                                # Create visualization using PyVis
                                if nodes:
                                    st.markdown("---")
                                    st.markdown("#### 🔗 Graph Visualization")
                                    st.caption("💡 Tip: Drag nodes, zoom with scroll, hover for details")
                                    
                                    try:
                                        from pyvis.network import Network
                                        
                                        # Enhanced network with physics
                                        net = Network(
                                            height="700px",
                                            width="100%",
                                            bgcolor="#fafafa",
                                            font_color="#1a1a1a",
                                            notebook=False,
                                            directed=True
                                        )
                                        
                                        # Configure physics for better layout
                                        net.set_options("""
                                        {
                                          "physics": {
                                            "enabled": true,
                                            "barnesHut": {
                                              "gravitationalConstant": -80000,
                                              "centralGravity": 0.3,
                                              "springLength": 200,
                                              "springConstant": 0.04,
                                              "damping": 0.09
                                            },
                                            "stabilization": {
                                              "iterations": 150
                                            }
                                          },
                                          "nodes": {
                                            "shape": "dot",
                                            "size": 20,
                                            "font": {
                                              "size": 14,
                                              "face": "Tahoma"
                                            },
                                            "borderWidth": 2,
                                            "shadow": true
                                          },
                                          "edges": {
                                            "width": 2,
                                            "arrows": {
                                              "to": {
                                                "enabled": true,
                                                "scaleFactor": 0.5
                                              }
                                            },
                                            "smooth": {
                                              "type": "continuous"
                                            },
                                            "font": {
                                              "size": 10,
                                              "align": "middle"
                                            }
                                          },
                                          "interaction": {
                                            "hover": true,
                                            "tooltipDelay": 100,
                                            "navigationButtons": true,
                                            "keyboard": true
                                          }
                                        }
                                        """)
                                        
                                        # Color mapping for different node types
                                        color_map = {
                                            "ENTITY": "#3b82f6",      # Blue
                                            "COMMUNITY": "#10b981",   # Green
                                            "DOCUMENT": "#f59e0b",    # Orange
                                            "CHUNK": "#8b5cf6",       # Purple
                                            "PERSON": "#ef4444",      # Red
                                            "ORGANIZATION": "#06b6d4", # Cyan
                                            "LOCATION": "#84cc16",    # Lime
                                        }
                                        
                                        # Add nodes with enhanced styling
                                        for node in nodes:
                                            node_type = node.get("type", "Node")
                                            color = color_map.get(node_type, "#6b7280")
                                            
                                            # Calculate size based on connections (degree)
                                            degree = sum(1 for e in edges if e["from"] == node["id"] or e["to"] == node["id"])
                                            size = 15 + (degree * 3)  # Bigger nodes for more connected entities
                                            
                                            net.add_node(
                                                node["id"],
                                                label=str(node["label"])[:30],  # Truncate long labels
                                                title=f"<b>{node_type}</b><br>" + "<br>".join([f"{k}: {v}" for k, v in list(node['properties'].items())[:5]]),
                                                color=color,
                                                size=size
                                            )
                                        
                                        # Add edges with labels
                                        for edge in edges:
                                            net.add_edge(
                                                edge["from"],
                                                edge["to"],
                                                label=edge["label"][:20],  # Truncate long labels
                                                title=f"<b>{edge['label']}</b><br>" + "<br>".join([f"{k}: {v}" for k, v in list(edge['properties'].items())[:3]]),
                                                color="#94a3b8"
                                            )
                                        
                                        # Save and display
                                        net.save_graph("neo4j_graph.html")
                                        with open("neo4j_graph.html", "r", encoding="utf-8") as f:
                                            html_content = f.read()
                                        
                                        # Enhanced iframe styling
                                        st.markdown("""
                                        <style>
                                            .neo4j-graph iframe {
                                                border: 2px solid #e5e7eb;
                                                border-radius: 12px;
                                                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                            }
                                        </style>
                                        """, unsafe_allow_html=True)
                                        
                                        components.html(html_content, height=720, scrolling=False)
                                        
                                        # Clean up
                                        if os.path.exists("neo4j_graph.html"):
                                            os.remove("neo4j_graph.html")
                                    
                                        # Add legend
                                        st.markdown("---")
                                        st.markdown("**📌 Legend:**")
                                        legend_cols = st.columns(4)
                                        legend_items = [
                                            ("🔵 ENTITY", "Entities extracted from text"),
                                            ("🟢 COMMUNITY", "Entity communities"),
                                            ("🟠 DOCUMENT", "Source documents"),
                                            ("🟣 CHUNK", "Text chunks"),
                                            ("🔴 PERSON", "People"),
                                            ("🔷 ORGANIZATION", "Organizations"),
                                            ("🟩 LOCATION", "Locations"),
                                        ]
                                        for idx, (label, desc) in enumerate(legend_items):
                                            with legend_cols[idx % 4]:
                                                st.caption(f"{label}")
                                    
                                    except ImportError:
                                        st.error("❌ PyVis not installed. Run: `pip install pyvis`")
                                
                                # Display raw data with better formatting
                                with st.expander("📄 View Raw Data (JSON)"):
                                    tab1, tab2 = st.tabs(["Nodes", "Relationships"])
                                    with tab1:
                                        st.json(nodes)
                                    with tab2:
                                        st.json(edges)
                                
                                # Download options
                                st.markdown("---")
                                col1, col2 = st.columns(2)
                                with col1:
                                    # Download as JSON
                                    import json as json_lib
                                    graph_data = json_lib.dumps({"nodes": nodes, "edges": edges}, indent=2)
                                    st.download_button(
                                        label="⬇️ Download Graph Data (JSON)",
                                        data=graph_data,
                                        file_name="neo4j_graph_data.json",
                                        mime="application/json",
                                        use_container_width=True
                                    )
                        
                        driver.close()
                        
                    except Exception as e:
                        st.error(f"Query execution failed: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

# Tab 4: Graph Visualization
with tab4:
    st.markdown("### Knowledge Graph Visualization")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Visualize the entire knowledge graph with interactive nodes and relationships")
    with col2:
        if st.button("Generate Visualization", type="primary", use_container_width=True):
            with st.spinner("Generating graph visualization..."):
                try:
                    # Check if graph file exists
                    import os
                    from config import WORKING_DIR
                    graphml_path = os.path.join(WORKING_DIR, "graph_chunk_entity_relation.graphml")
                    
                    if not os.path.exists(graphml_path):
                        st.error("No graph data found. Please index some documents first.")
                    else:
                        # Import visualization function
                        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from visualize import visualize_graph
                        
                        # Generate visualization
                        output_path = visualize_graph(
                            working_dir=WORKING_DIR,
                            output_file="graph_visualization_streamlit.html"
                        )
                        
                        if output_path and os.path.exists(output_path):
                            st.success("Graph visualization generated successfully!")
                            st.session_state["graph_viz_path"] = output_path
                        else:
                            st.error("Failed to generate visualization.")
                
                except Exception as e:
                    st.error(f"Error generating visualization: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Display visualization if it exists
    if "graph_viz_path" in st.session_state and os.path.exists(st.session_state["graph_viz_path"]):
        st.markdown("---")
        
        # Graph statistics
        try:
            import networkx as nx
            from config import WORKING_DIR
            graphml_path = os.path.join(WORKING_DIR, "graph_chunk_entity_relation.graphml")
            G = nx.read_graphml(graphml_path)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Nodes", f"{G.number_of_nodes():,}")
            with col2:
                st.metric("Edges", f"{G.number_of_edges():,}")
            with col3:
                density = G.number_of_edges() / max(G.number_of_nodes(), 1)
                st.metric("Density", f"{density:.2f}")
            with col4:
                avg_degree = sum(dict(G.degree()).values()) / max(G.number_of_nodes(), 1)
                st.metric("Avg Degree", f"{avg_degree:.1f}")
        except:
            pass
        
        st.markdown("---")
        st.markdown("#### Interactive Graph")
        st.caption("💡 Tip: Drag nodes, zoom with mouse wheel, click to select")
        
        # Read HTML file
        with open(st.session_state["graph_viz_path"], "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Display in iframe with better styling
        st.markdown("""
        <style>
            iframe {
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
        </style>
        """, unsafe_allow_html=True)
        
        components.html(html_content, height=850, scrolling=False)
        
        # Download button
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            with open(st.session_state["graph_viz_path"], "rb") as f:
                st.download_button(
                    label="Download HTML",
                    data=f,
                    file_name="knowledge_graph.html",
                    mime="text/html",
                    use_container_width=True
                )
    else:
        st.markdown("---")
        st.info("Click 'Generate Visualization' to create an interactive graph view.")
        
        # Show graph stats
        try:
            response = requests.get(f"{API_BASE_URL}/graph_stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Nodes", f"{stats.get('nodes', 0):,}")
                with col2:
                    st.metric("Total Edges", f"{stats.get('edges', 0):,}")
                with col3:
                    density = stats.get('edges', 0) / max(stats.get('nodes', 1), 1)
                    st.metric("Graph Density", f"{density:.2f}")
        except:
            pass

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #9ca3af; font-size: 0.875rem; padding: 1rem 0;'>
    Financial Intelligence Platform v2.0 | 
    <a href='http://localhost:8000/docs' target='_blank' style='color: #6b7280; text-decoration: none;'>API Documentation</a>
</div>
""", unsafe_allow_html=True)
