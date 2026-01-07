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
tab1, tab2, tab3, tab4 = st.tabs(["Query", "Data Ingestion", "Data Sources", "Graph Visualization"])

# Tab 1: Query Interface
with tab1:
    st.markdown("### Query Interface")
    
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
                mode_text = f"<div class='message-mode'>Mode: {message.get('mode', 'N/A')}</div>" if "mode" in message else ""
                st.markdown(f"""
                <div class="assistant-message">
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
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
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
            st.warning("Neo4j connection not configured. Please set NEO4J_URI and NEO4J_PASSWORD in your .env file.")
        else:
            st.info(f"Connected to: {neo4j_uri}")
            
            # Query input
            cypher_query = st.text_area(
                "Enter Cypher Query",
                value="MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50",
                height=100,
                help="Enter a Cypher query to visualize the graph"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                execute_button = st.button("Execute Query", type="primary")
            with col2:
                if st.button("Clear Graph", type="secondary"):
                    if "neo4j_results" in st.session_state:
                        del st.session_state["neo4j_results"]
                    st.rerun()
            
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
                                    try:
                                        from pyvis.network import Network
                                        
                                        net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="#000000")
                                        net.barnes_hut()
                                        
                                        # Add nodes
                                        for node in nodes:
                                            net.add_node(
                                                node["id"],
                                                label=str(node["label"]),
                                                title=f"{node['type']}: {json.dumps(node['properties'], indent=2)}",
                                                color="#3b82f6"
                                            )
                                        
                                        # Add edges
                                        for edge in edges:
                                            net.add_edge(
                                                edge["from"],
                                                edge["to"],
                                                label=edge["label"],
                                                title=json.dumps(edge["properties"], indent=2)
                                            )
                                        
                                        # Save and display
                                        net.save_graph("neo4j_graph.html")
                                        with open("neo4j_graph.html", "r", encoding="utf-8") as f:
                                            html_content = f.read()
                                        components.html(html_content, height=600, scrolling=True)
                                        
                                        # Clean up
                                        if os.path.exists("neo4j_graph.html"):
                                            os.remove("neo4j_graph.html")
                                    
                                    except ImportError:
                                        st.error("PyVis not installed. Run: pip install pyvis")
                                
                                # Display raw data
                                with st.expander("View Raw Data"):
                                    st.json({
                                        "nodes": nodes,
                                        "edges": edges
                                    })
                        
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
