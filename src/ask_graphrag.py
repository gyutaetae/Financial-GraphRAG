# requests는 HTTP 요청을 보내는 도구예요!
# 마치 "다른 서버에 요청을 보내는 우체국" 같은 거예요!
import requests
# sys는 시스템 관련 작업을 하는 도구예요!
import sys

def ask_graph_rag(question, mode="local"):
    """
    GraphRAG API에 질문을 보내고 답변을 받는 함수예요!
    
    Args:
        question: 질문 내용
        mode: "api" (OpenAI API 사용) 또는 "local" (Ollama 로컬 사용, 기본값)
    
    Returns:
        API 응답 결과 (dict)
    """
    url = "http://127.0.0.1:8000/query"
    
    # 1. Request Body 구성
    # mode를 'api'로 하면 OpenAI API를 사용해서 더 정확한 답변을,
    # 'local'로 하면 Ollama 로컬 모델을 사용해요! (기본값: "local")
    payload = {
        "question": question,
        "mode": mode  # "api" 또는 "local"
    }
    
    try:
        # 2. API 호출
        # requests.post()는 POST 요청을 보내는 거예요!
        # json=payload는 "JSON 형식으로 데이터를 보낸다"는 뜻이에요!
        print(f"🔍 질문: {question}")
        print(f"🔧 모드: {mode}")
        
        # mode가 "local"이면 Ollama 서버가 실행 중인지 확인해요!
        if mode == "local":
            try:
                ollama_check = requests.get("http://localhost:11434/api/tags", timeout=2)
                if ollama_check.status_code != 200:
                    print("⚠️  Ollama 서버가 실행되지 않았어요!")
                    print("💡 'ollama serve' 명령어로 서버를 시작하거나, 'api' 모드를 사용해주세요!")
            except:
                print("⚠️  Ollama 서버에 연결할 수 없어요!")
                print("💡 'ollama serve' 명령어로 서버를 시작하거나, 'api' 모드를 사용해주세요!")
        
        print(f"⏳ 답변 생성 중...")
        
        response = requests.post(url, json=payload, timeout=120)  # 타임아웃 120초
        
        # response.raise_for_status()는 "응답이 성공적이지 않으면 에러를 발생시켜"라는 뜻이에요!
        response.raise_for_status()
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n🤖 AI의 답변 ({result['mode']} 모드):")
            print("=" * 60)
            print(result['answer'])
            print("=" * 60)
            return result
        else:
            print(f"❌ 에러 발생: {response.status_code}")
            print(f"응답: {response.text}")
            return {"error": response.text, "status": "error"}
            
    except requests.exceptions.RequestException as e:
        # requests.exceptions.RequestException은 "HTTP 요청 관련 에러"예요!
        error_msg = f"HTTP 요청 에러: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg, "status": "error"}
    except Exception as e:
        # Exception은 "모든 종류의 에러"예요!
        error_msg = f"예상치 못한 에러: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg, "status": "error"}

# if __name__ == "__main__": 이건 "이 파일을 직접 실행했을 때만"이라는 뜻이에요!
if __name__ == "__main__":
    # sys.argv는 "명령줄에서 입력한 인자들"이에요!
    # 예: python3 ask_graphrag.py "질문 내용" local
    #     sys.argv[0] = "ask_graphrag.py"
    #     sys.argv[1] = "질문 내용"
    #     sys.argv[2] = "local" (선택사항)
    
    if len(sys.argv) < 2:
        # 질문이 입력되지 않았으면 사용법을 알려줘요!
        print("=" * 60)
        print("📚 사용법:")
        print("=" * 60)
        print("python3 src/ask_graphrag.py \"<질문>\" [mode]")
        print()
        print("예시:")
        print("  python3 src/ask_graphrag.py \"엔비디아의 매출은?\"")
        print("  python3 src/ask_graphrag.py \"엔비디아의 매출은?\" local")
        print("  python3 src/ask_graphrag.py \"엔비디아의 매출은?\" api")
        print()
        print("mode 옵션:")
        print("  - local: Ollama 로컬 모델 사용 (기본값, 빠르고 무료)")
        print("  - api: OpenAI API 사용 (더 정확하지만 유료)")
        print("=" * 60)
        
        # 기본 질문으로 테스트
        print("\n💡 기본 질문으로 테스트해볼까요?")
        print("=" * 60)
        ask_graph_rag("What is NVIDIA revenue?", "local")
    else:
        # sys.argv[1]은 "첫 번째 인자(질문)"예요!
        question = sys.argv[1]
        
        # sys.argv[2]는 "두 번째 인자(mode)"예요! (선택사항)
        mode = sys.argv[2] if len(sys.argv) > 2 else "local"
        
        # mode가 올바른지 확인해요!
        if mode not in ["api", "local"]:
            print(f"⚠️  잘못된 mode: {mode}")
            print("💡 'api' 또는 'local'만 사용할 수 있어요. 기본값 'local'을 사용할게요!")
            mode = "local"
        
        print("=" * 60)
        print("🚀 GraphRAG 질문-답변 시작")
        print("=" * 60)
        
        # ask_graph_rag 함수를 호출해요!
        result = ask_graph_rag(question, mode)
        
        print()
        print("=" * 60)
        print("📊 최종 결과:")
        print("=" * 60)
        # json.dumps()는 딕셔너리를 JSON 문자열로 변환하는 거예요!
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))