import streamlit as st
import requests
import sys
import os
import streamlit.components.v1 as components
import time
import json
from datetime import datetime

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
tab1, tab2, tab3 = st.tabs(["Query", "Data Ingestion", "Data Sources"])

# Tab 1: Query Interface
with tab1:
    st.markdown("### Query Interface")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "mode" in message:
                st.caption(f"Mode: {message['mode']}")
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your data..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/query",
                        json={"question": prompt, "mode": query_mode},
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        answer = result.get("answer", "No response generated.")
                        mode = result.get('mode', 'unknown').upper()
                        
                        st.markdown(answer)
                        st.caption(f"Mode: {mode}")
                        
                        # Add assistant response to chat history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "mode": mode
                        })
                    else:
                        error_msg = f"Error {response.status_code}: {response.text}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                except Exception as e:
                    error_msg = f"Query failed: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    # Clear chat button
    if st.session_state.messages:
        if st.button("Clear Chat History", type="secondary"):
            st.session_state.messages = []
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

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #9ca3af; font-size: 0.875rem; padding: 1rem 0;'>
    Financial Intelligence Platform v2.0 | 
    <a href='http://localhost:8000/docs' target='_blank' style='color: #6b7280; text-decoration: none;'>API Documentation</a>
</div>
""", unsafe_allow_html=True)
