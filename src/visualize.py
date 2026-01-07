# visualize.py는 "그래프를 시각화하는" 파일이에요!
# 마치 "그래프를 예쁘게 그려주는 도구" 같은 거예요!

# networkx는 그래프를 다루는 도구예요!
# 마치 "그래프를 읽고 쓸 수 있는 도구" 같은 거예요!
import networkx as nx
# pyvis는 그래프를 인터랙티브하게 시각화하는 도구예요!
# 마치 "그래프를 웹페이지로 보여주는 도구" 같은 거예요!
from pyvis.network import Network
# os는 파일 경로를 다루는 도구예요!
import os
# sys는 시스템 관련 작업을 하는 도구예요!
import sys

def visualize_graph(working_dir="./graph_storage_hybrid", output_file="graph_ui.html"):
    """
    GraphRAG 그래프를 시각화하는 함수예요!
    
    Args:
        working_dir: 그래프 데이터가 있는 폴더 경로
        output_file: 생성할 HTML 파일 이름
        
    Returns:
        생성된 HTML 파일 경로
    """
    try:
        # 1. 그래프 파일 경로
        graphml_path = os.path.join(working_dir, "graph_chunk_entity_relation.graphml")
        
        # 파일이 있는지 확인해요!
        if not os.path.exists(graphml_path):
            print(f"❌ 그래프 파일을 찾을 수 없어요: {graphml_path}")
            print("💡 먼저 텍스트를 인덱싱해서 그래프를 만들어주세요!")
            return None
        
        print(f"📖 그래프 파일 읽는 중: {graphml_path}")
        
        # 2. GraphML 파일을 읽어서 NetworkX 그래프로 변환해요!
        # nx.read_graphml()은 GraphML 파일을 읽어서 그래프로 만드는 거예요!
        G = nx.read_graphml(graphml_path)
        
        print(f"✅ 그래프 로드 완료!")
        print(f"   - 노드 수: {G.number_of_nodes()}")
        print(f"   - 엣지 수: {G.number_of_edges()}")
        
        # 3. Pyvis Network 객체 생성
        net = Network(
            notebook=False,
            height="800px",
            width="100%",
            bgcolor="#1f2937",  # 다크 그레이
            font_color="#f3f4f6",  # 밝은 회색
            directed=True  # 방향성 그래프
        )
        
        # 4. NetworkX 그래프를 Pyvis로 변환해요!
        # net.from_nx()는 NetworkX 그래프를 Pyvis 형식으로 변환하는 거예요!
        net.from_nx(G)
        
        # 5. 노드 스타일 설정 (더 예쁘게 만들기!)
        # 노드 타입에 따라 색상을 다르게 설정해요!
        node_colors = {
            "ORGANIZATION": "#10b981",  # 회사 - 에메랄드
            "PERSON": "#ef4444",        # 사람 - 빨강
            "GEO": "#06b6d4",           # 지역 - 시안
            "TECHNOLOGY": "#3b82f6",    # 기술 - 파랑
            "REVENUE": "#f59e0b",       # 매출 - 주황
            "FINANCIAL": "#8b5cf6",     # 금융 - 보라
            "PRODUCT": "#ec4899",       # 제품 - 핑크
            "DATE": "#14b8a6",          # 날짜 - 청록
        }
        
        # 각 노드에 색상과 크기 설정해요!
        for node in net.nodes:
            node_id = str(node.get("id", ""))
            node_label = str(node.get("label", node_id))
            
            # 노드 ID에서 따옴표 제거
            clean_id = node_id.strip('"')
            clean_label = node_label.strip('"')
            
            # 노드 타입 추출 (entity_type 속성 확인)
            node_type = None
            if hasattr(node, 'get'):
                node_type = node.get("entity_type", "")
            
            # 노드 색상 결정
            node_color = "#6b7280"  # 기본 색상 (회색)
            for entity_type, color in node_colors.items():
                if entity_type.upper() in clean_id.upper() or entity_type.upper() in clean_label.upper():
                    node_color = color
                    break
                if node_type and entity_type.upper() in str(node_type).upper():
                    node_color = color
                    break
            
            # 노드 크기 (중요한 노드는 크게)
            node_size = 25
            if any(keyword in clean_label.upper() for keyword in ["NVIDIA", "REVENUE", "INCOME", "PROFIT"]):
                node_size = 40
            
            # 노드 스타일 설정
            node["color"] = {
                "background": node_color,
                "border": "#ffffff",
                "highlight": {"background": node_color, "border": "#fbbf24"}
            }
            node["size"] = node_size
            node["font"] = {"size": 14, "color": "#ffffff", "face": "arial"}
            node["label"] = clean_label[:50]  # 라벨 길이 제한
            node["title"] = f"{clean_label}\n\nType: {node_type or 'Unknown'}"  # 호버 시 표시
        
        # 6. 엣지 스타일 설정
        for edge in net.edges:
            edge["color"] = {
                "color": "#94a3b8",
                "highlight": "#3b82f6",
                "opacity": 0.6
            }
            edge["width"] = 2
            edge["smooth"] = {"type": "continuous"}
        
        # 7. 물리 엔진 및 인터랙션 설정
        net.set_options("""
        {
          "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 3,
            "shadow": {
              "enabled": true,
              "color": "rgba(0,0,0,0.3)",
              "size": 10,
              "x": 2,
              "y": 2
            }
          },
          "edges": {
            "smooth": {
              "enabled": true,
              "type": "continuous"
            },
            "arrows": {
              "to": {
                "enabled": true,
                "scaleFactor": 0.5
              }
            }
          },
          "physics": {
            "enabled": true,
            "barnesHut": {
              "gravitationalConstant": -8000,
              "centralGravity": 0.3,
              "springLength": 150,
              "springConstant": 0.04,
              "damping": 0.09,
              "avoidOverlap": 0.1
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "barnesHut",
            "stabilization": {
              "enabled": true,
              "iterations": 200,
              "updateInterval": 25
            }
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": true,
            "keyboard": {
              "enabled": true
            },
            "zoomView": true,
            "dragView": true
          }
        }
        """)
        
        # 8. HTML 파일로 저장해요!
        # net.write_html()는 HTML 파일을 생성하는 거예요!
        output_path = os.path.abspath(output_file)
        # notebook=False로 설정해서 일반 HTML 파일로 생성해요!
        net.write_html(output_path, notebook=False)
        
        print(f"🎨 그래프 시각화 완료!")
        print(f"📄 파일 위치: {output_path}")
        print(f"🌐 브라우저에서 열어보세요!")
        
        return output_path
        
    except FileNotFoundError as e:
        print(f"❌ 파일을 찾을 수 없어요: {e}")
        return None
    except Exception as e:
        print(f"❌ 에러 발생: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

# if __name__ == "__main__": 이건 "이 파일을 직접 실행했을 때만"이라는 뜻이에요!
if __name__ == "__main__":
    # sys.argv는 "명령줄에서 입력한 인자들"이에요!
    # 예: python3 visualize.py graph_storage_hybrid
    #     sys.argv[0] = "visualize.py"
    #     sys.argv[1] = "graph_storage_hybrid" (선택사항)
    
    # working_dir은 명령줄 인자로 받거나 기본값 사용해요!
    working_dir = sys.argv[1] if len(sys.argv) > 1 else "./graph_storage_hybrid"
    
    print("=" * 60)
    print("🎨 GraphRAG 그래프 시각화")
    print("=" * 60)
    print(f"📁 작업 디렉토리: {working_dir}")
    print()
    
    # visualize_graph 함수를 호출해요!
    result = visualize_graph(working_dir=working_dir)
    
    if result:
        print()
        print("=" * 60)
        print("✅ 시각화 성공!")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ 시각화 실패!")
        print("=" * 60)