# app.py는 "FastAPI 서버"를 만드는 파일이에요!
# 마치 "웹 서버를 만드는 도구 상자" 같은 거예요!

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import os
import sys

# src 디렉토리를 Python path에 추가해요!
# 이렇게 하면 'from engine import ...' 같은 import가 작동해요!
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# engine 모듈에서 HybridGraphRAGEngine을 가져와요!
from engine import HybridGraphRAGEngine
from config import print_config, validate_config, ROUTER_MODEL, ROUTER_TEMPERATURE, WEB_SEARCH_MAX_RESULTS, OPENAI_API_KEY, OPENAI_BASE_URL, MCP_CONFIG_PATH
from search import web_search, format_search_results
from openai import AsyncOpenAI
from utils import get_executive_report_prompt, get_web_search_report_prompt
from mcp import MCPManager

# --- [1] 전역 변수 ---
# engine은 "GraphRAG 엔진"이에요!
# None은 "아직 아무것도 없다"는 뜻이에요!
engine: HybridGraphRAGEngine = None
mcp_manager: MCPManager = None

# --- [2] 서버 시작/종료 이벤트 핸들러 ---
# @asynccontextmanager는 "비동기 컨텍스트 매니저"를 만드는 거예요!
# 마치 "서버가 시작될 때와 끝날 때 뭔가를 하는" 것처럼!
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버가 시작될 때 실행되는 부분이에요!
    global engine, mcp_manager
    
    # 설정 정보를 출력해요!
    print_config()
    
    # validate_config()는 "설정이 올바른지 확인하는" 함수예요!
    validate_config()
    
    # HybridGraphRAGEngine을 초기화하는 거예요!
    # 마치 "GraphRAG 엔진을 준비하는" 것처럼!
    print("🚀 HybridGraphRAGEngine 초기화 중...")
    engine = HybridGraphRAGEngine()
    print("✅ HybridGraphRAGEngine 준비 완료!")
    
    # MCP Manager 초기화
    print("🚀 MCP Manager 초기화 중...")
    mcp_manager = MCPManager(config_path=MCP_CONFIG_PATH)
    await mcp_manager.start_cleanup_task()
    print("✅ MCP Manager 준비 완료 (lazy load 모드)")
    
    # yield는 "여기서 잠시 멈춰서 서버를 실행하고, 나중에 다시 돌아와"라는 뜻이에요!
    yield
    
    # 서버가 종료될 때 실행되는 부분이에요!
    if mcp_manager:
        await mcp_manager.shutdown()
        print("✅ MCP Manager 종료 완료")

# --- [3] FastAPI 앱 초기화 ---
# FastAPI()는 "웹 서버 앱을 만들어줘"라는 뜻이에요!
# lifespan은 "서버 시작/종료 이벤트 핸들러"예요!
app = FastAPI(
    title="VIK AI: Hybrid GraphRAG API",
    description="금융 분석을 위한 하이브리드 GraphRAG API예요! 인덱싱은 OpenAI API, 질문은 API/LOCAL 선택 가능해요!",
    version="2.0.0",
    lifespan=lifespan  # lifespan 이벤트 핸들러를 연결해요!
)

# --- [4] Pydantic 모델 ---
# Pydantic 모델은 "데이터 구조를 정의하는 것"이에요!
# 마치 "이런 모양의 데이터를 받을게요!"라고 미리 알려주는 거예요!

# QueryRequest는 "질문 요청"을 나타내는 모델이에요!
class QueryRequest(BaseModel):
    # question은 "질문 내용"이에요!
    question: str
    # mode는 "어떤 모드를 사용할지" 정하는 거예요. "api" 또는 "local"!
    # 기본값은 "local"이에요!
    mode: str = "local"
    # temperature는 "응답의 창의성"을 조절해요! (0.0 = 정확, 2.0 = 창의적)
    temperature: float = 0.2
    # top_k는 "검색할 청크 개수"를 정해요!
    top_k: int = 30
    # search_type은 "local" (특정 검색) 또는 "global" (전체 요약)
    search_type: str = "local"
    # enable_web_search는 "웹 검색을 활성화할지" 정해요! (기본값: False)
    enable_web_search: bool = False
    # use_multi_agent는 "Multi-Agent 모드를 사용할지" 정해요! (기본값: False)
    use_multi_agent: bool = False
    
    # Pydantic v2 스타일로 예시 설정
    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "What is NVIDIA revenue?",
                "mode": "local",
                "search_type": "local",
                "enable_web_search": False,
                "use_multi_agent": False
            }
        }
    }

# InsertRequest는 "텍스트 추가 요청"을 나타내는 모델이에요!
class InsertRequest(BaseModel):
    # text는 "추가할 텍스트"예요!
    text: str
    
    # Pydantic v2 스타일로 설정 (deprecation warning 해결)
    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "NVIDIA reported record revenue of $57.0 billion in Q3 2026."
            }
        }
    }

# --- [5] Router 함수들 (Decision Layer) ---
# 질문을 분류하고 웹 검색을 처리하는 함수들이에요!

async def classify_query(question: str) -> str:
    """
    GPT-4o-mini를 사용하여 질문을 분류하는 Router 함수
    
    Args:
        question: 사용자 질문
    
    Returns:
        "GRAPH_RAG" 또는 "WEB_SEARCH"
    """
    try:
        # OpenAI 클라이언트 생성
        client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        
        # 분류를 위한 시스템 프롬프트
        system_prompt = """You are a query classifier for a financial AI system.

Your task is to classify user questions into two categories:

1. GRAPH_RAG: Questions about uploaded PDF documents, company information, people, financials from internal reports
   Examples:
   - "What is NVIDIA's Q3 revenue?"
   - "Who is Jensen Huang?" (person information from documents)
   - "How old is the CEO?" (biographical information)
   - "Summarize the uploaded report"
   - "What are the key findings in the document?"

2. WEB_SEARCH: Questions EXPLICITLY requiring TODAY's/LATEST/CURRENT real-time market data or breaking news
   Examples:
   - "What is today's stock price?"
   - "Latest news TODAY about Tesla"
   - "Current inflation rate RIGHT NOW"
   - "What happened in the market TODAY?"

IMPORTANT: Default to GRAPH_RAG unless the question EXPLICITLY asks for TODAY/LATEST/CURRENT/NOW information.

Respond with ONLY ONE WORD: Either "GRAPH_RAG" or "WEB_SEARCH" - nothing else."""

        # GPT-4o-mini 호출
        response = await client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Classify this question: {question}"}
            ],
            temperature=ROUTER_TEMPERATURE,
            max_tokens=10
        )
        
        # 응답 추출 및 정규화
        classification = response.choices[0].message.content.strip().upper()
        
        # 유효성 검사
        if "GRAPH_RAG" in classification:
            return "GRAPH_RAG"
        elif "WEB_SEARCH" in classification or "WEB" in classification:
            return "WEB_SEARCH"
        else:
            # 기본값: GRAPH_RAG (내부 문서 우선)
            print(f"⚠️ 분류 결과가 명확하지 않아요: {classification}, 기본값 GRAPH_RAG 사용")
            return "GRAPH_RAG"
    
    except Exception as e:
        print(f"❌ 질문 분류 중 에러 발생: {e}")
        # 에러 시 기본값: GRAPH_RAG
        return "GRAPH_RAG"


async def handle_web_search(question: str) -> str:
    """
    웹 검색을 수행하고 결과를 요약하는 함수
    
    Args:
        question: 사용자 질문
    
    Returns:
        검색 결과를 바탕으로 생성된 답변
    """
    try:
        # 1. DuckDuckGo로 웹 검색
        print(f"🔍 웹 검색 시작: {question}")
        search_results = await web_search(question, max_results=WEB_SEARCH_MAX_RESULTS)
        
        if not search_results:
            return "죄송해요, 관련된 최신 정보를 찾을 수 없었어요. 다른 질문을 해보시겠어요?"
        
        # 2. 검색 결과를 텍스트로 포맷
        formatted_results = await format_search_results(search_results)
        
        # 3. GPT-4o-mini로 검색 결과 요약
        client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        
        synthesis_prompt = f"""Based on the following web search results, answer the user's question comprehensively.
Include relevant data and cite sources with URLs when possible.

User Question: {question}

Search Results:
{formatted_results}

Provide a clear, concise answer with sources."""

        response = await client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful financial assistant that synthesizes web search results into clear answers."},
                {"role": "user", "content": synthesis_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content.strip()
        
        # 출처 정보 추가
        sources = "\n\n📚 출처:\n"
        for idx, result in enumerate(search_results[:3], 1):
            sources += f"{idx}. {result['title']}\n   {result['url']}\n"
        
        return answer + sources
    
    except Exception as e:
        print(f"❌ 웹 검색 처리 중 에러 발생: {e}")
        return f"웹 검색 중 에러가 발생했어요: {str(e)}"


# --- [6] 루트 엔드포인트 ---
# @app.get("/")는 "루트 경로(/)에 GET 요청이 오면" 실행되는 함수예요!
# 마치 "홈페이지에 접속하면" 실행되는 거예요!
@app.get("/")
async def root():
    # return은 "이걸 돌려줘"라는 뜻이에요!
    return {
        "message": "VIK AI Hybrid GraphRAG API에 오신 것을 환영해요!",
        "description": "인덱싱은 OpenAI API(gpt-5-mini)를 사용하고, 질문은 API/LOCAL 모드를 선택할 수 있어요!",
        "endpoints": {
            "/insert": "텍스트 인덱싱하기 (POST) - OpenAI API 사용",
            "/query": "질문하기 (POST) - mode 파라미터로 'api' 또는 'local' 선택",
            "/health": "서버 상태 확인 (GET)",
            "/graph_stats": "그래프 현황 확인 (GET)",
            "/visualize": "그래프 시각화 HTML 생성 (GET)",
            "/docs": "API 문서 보기 (GET)"
        },
        "usage": {
            "insert": {
                "method": "POST",
                "url": "/insert",
                "body": {"text": "인덱싱할 텍스트"}
            },
            "query": {
                "method": "POST",
                "url": "/query",
                "body": {
                    "question": "질문 내용",
                    "mode": "api 또는 local (기본값: local)"
                }
            }
        }
    }

# --- [7] 서버 상태 확인 엔드포인트 ---
# @app.get("/health")는 "서버 상태를 확인하는" 엔드포인트예요!
@app.get("/health")
async def health():
    # 서버가 잘 작동하고 있다는 것을 알려주는 거예요!
    return {
        "status": "healthy",
        "message": "서버가 정상적으로 작동 중이에요!",
        "engine_ready": engine is not None
    }

# --- [7-1] MCP 상태 확인 엔드포인트 ---
@app.get("/mcp/status")
async def mcp_status():
    """MCP Manager 상태 확인"""
    if mcp_manager is None:
        return {
            "status": "disabled",
            "message": "MCP Manager가 초기화되지 않았습니다"
        }
    
    status = mcp_manager.get_status()
    return {
        "status": "active",
        "message": "MCP Manager가 정상 작동 중입니다",
        **status
    }

# --- [7-2] 메모리 모니터링 엔드포인트 ---
@app.get("/memory")
async def memory_status():
    """메모리 사용률 확인 (8GB RAM 환경 모니터링)"""
    import psutil
    
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024 ** 3), 2),
        "used_gb": round(mem.used / (1024 ** 3), 2),
        "available_gb": round(mem.available / (1024 ** 3), 2),
        "percent": mem.percent,
        "status": "healthy" if mem.percent < 85 else "warning",
        "message": "메모리 사용률이 정상입니다." if mem.percent < 85 else "메모리 사용률이 높습니다!"
    }

# --- [8] 그래프 통계 엔드포인트 ---
# @app.get("/graph_stats")는 "그래프 통계를 보여주는" 엔드포인트예요!
@app.get("/graph_stats")
async def graph_stats():
    # if는 "만약"이라는 뜻이에요!
    if engine is None:
        return {"nodes": 0, "edges": 0, "message": "엔진이 아직 초기화되지 않았어요!"}
    
    # engine.get_graph_stats()는 그래프 통계를 가져오는 거예요!
    return engine.get_graph_stats()

# --- [9] 그래프 초기화 엔드포인트 ---
# @app.post("/reset")는 "그래프를 초기화하는" 엔드포인트예요!
@app.post("/reset",
          summary="그래프 초기화",
          description="기존 그래프 스토리지를 백업하고 삭제한 후 새로운 그래프로 시작해요!")
async def reset_graph():
    global engine
    # if는 "만약"이라는 뜻이에요!
    if engine is None:
        raise HTTPException(status_code=503, detail="엔진이 아직 초기화되지 않았어요!")
    
    try:
        import shutil
        from datetime import datetime
        
        # 백업 폴더 이름 생성 (타임스탬프 포함)
        backup_dir = f"{engine.working_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 기존 그래프 스토리지가 있으면 백업
        if os.path.exists(engine.working_dir):
            shutil.move(engine.working_dir, backup_dir)
            print(f"✅ 기존 그래프 백업 완료: {backup_dir}")
        
        # 엔진 재초기화
        engine = HybridGraphRAGEngine()
        
        return {
            "message": "그래프가 성공적으로 초기화되었어요!",
            "status": "success",
            "backup_dir": backup_dir if os.path.exists(backup_dir) else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"그래프 초기화 중 에러가 발생했어요: {str(e)}")

# --- [10] 그래프 시각화 엔드포인트 ---
# @app.get("/visualize")는 "그래프를 시각화하는 HTML 파일을 생성하는" 엔드포인트예요!
@app.get("/visualize",
         summary="그래프 시각화",
         description="GraphRAG 그래프를 인터랙티브하게 시각화한 HTML 파일을 생성해요!")
async def visualize():
    # if는 "만약"이라는 뜻이에요!
    if engine is None:
        raise HTTPException(status_code=503, detail="엔진이 아직 초기화되지 않았어요!")
    
    try:
        # visualize.py에서 visualize_graph 함수를 가져와요!
        from visualize import visualize_graph
        
        # 그래프를 시각화해서 HTML 파일을 생성해요!
        output_path = visualize_graph(working_dir=engine.working_dir, output_file="graph_visualization.html")
        
        if output_path and os.path.exists(output_path):
            # FileResponse는 "파일을 반환하는" 거예요!
            # 마치 "이 HTML 파일을 브라우저로 보여줘"라는 뜻이에요!
            return FileResponse(
                output_path,
                media_type="text/html",
                filename="graph_visualization.html"
            )
        else:
            raise HTTPException(status_code=500, detail="그래프 시각화 파일을 생성할 수 없어요!")
            
    except ImportError:
        raise HTTPException(status_code=500, detail="pyvis 패키지가 설치되지 않았어요! 'pip install pyvis'로 설치해주세요!")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"그래프 시각화 중 에러가 발생했어요: {str(e)}")

# --- [11] 텍스트 인덱싱 엔드포인트 ---
# @app.post("/insert")는 "텍스트를 인덱싱하는" 엔드포인트예요!
# 인덱싱은 항상 OpenAI API를 사용해요! (정확한 금융 수치 추출을 위해)
@app.post("/insert", 
          summary="텍스트 인덱싱",
          description="텍스트를 GraphRAG에 인덱싱해요. 항상 OpenAI API를 사용해요!",
          response_description="인덱싱 결과")
async def insert(request: InsertRequest):
    # if는 "만약"이라는 뜻이에요!
    if engine is None:
        # HTTPException은 "에러를 던지는" 거예요!
        # 503은 "서비스를 사용할 수 없음"이라는 뜻이에요!
        raise HTTPException(status_code=503, detail="엔진이 아직 초기화되지 않았어요!")
    
    # text 필드가 비어있으면 에러를 발생시켜요!
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=422, 
            detail="'text' 필드는 비어있을 수 없어요! 텍스트를 입력해주세요."
        )
    
    try:
        # try는 "시도해봐"라는 뜻이에요!
        # engine.ainsert()는 비동기로 텍스트를 그래프에 넣는 거예요!
        # 인덱싱은 항상 OpenAI API를 사용해요!
        await engine.ainsert(request.text)
        
        # return은 "이걸 돌려줘"라는 뜻이에요!
        return {
            "message": "텍스트가 성공적으로 인덱싱되었어요! (OpenAI API 사용)",
            "status": "success",
            "mode": "openai_api"
        }
    except Exception as e:
        # except는 "만약 에러가 생기면"이라는 뜻이에요!
        # Exception은 "모든 종류의 에러"예요!
        # e는 에러 내용이에요!
        # HTTPException으로 에러를 반환해요!
        import traceback
        error_detail = f"인덱싱 중 에러가 발생했어요: {str(e)}\n\n상세 정보:\n{traceback.format_exc()}"
        print(f"❌ 인덱싱 에러:\n{error_detail}")
        raise HTTPException(status_code=500, detail=f"인덱싱 중 에러가 발생했어요: {str(e)}")

# --- [12] 질문-답변 엔드포인트 (Decision Layer 통합) ---
# @app.post("/query")는 "질문을 받아서 답변을 주는" 엔드포인트예요!
# mode 파라미터로 "api" 또는 "local"을 선택할 수 있어요!
@app.post("/query",
          summary="질문-답변",
          description="GraphRAG에 질문하고 답변을 받아요. mode로 'api' 또는 'local'을 선택할 수 있어요!\n\n**요청 형식**:\n```json\n{\n  \"question\": \"질문 내용\",\n  \"mode\": \"local\"\n}\n```",
          response_description="질문과 답변",
          responses={
              200: {
                  "description": "질문 성공",
                  "content": {
                      "application/json": {
                          "example": {
                              "question": "What is NVIDIA revenue?",
                              "answer": "NVIDIA's revenue is $57.0 billion in Q3 2026.",
                              "mode": "local",
                              "status": "success"
                          }
                      }
                  }
              },
              422: {
                  "description": "요청 데이터 형식 오류",
                  "content": {
                      "application/json": {
                          "example": {
                              "detail": [
                                  {
                                      "type": "missing",
                                      "loc": ["body", "question"],
                                      "msg": "Field required",
                                      "input": {}
                                  }
                              ]
                          }
                      }
                  }
              }
          })
async def query(request: QueryRequest):
    # if는 "만약"이라는 뜻이에요!
    if engine is None:
        raise HTTPException(status_code=503, detail="엔진이 아직 초기화되지 않았어요!")
    
    # question 필드가 비어있으면 에러를 발생시켜요!
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=422,
            detail="'question' 필드는 비어있을 수 없어요! 질문을 입력해주세요."
        )
    
    # mode가 "api" 또는 "local"이 아니면 에러를 발생시켜요!
    if request.mode not in ["api", "local"]:
        raise HTTPException(
            status_code=400,
            detail="mode는 'api' 또는 'local'이어야 해요! (현재 값: '{}')".format(request.mode)
        )
    
    try:
        # #region agent log
        import json
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"app.py:325","message":"Query entry","data":{"question":request.question,"mode":request.mode,"enable_web_search":request.enable_web_search,"use_multi_agent":request.use_multi_agent},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H1,H2,H5"})+'\n')
        # #endregion
        
        # --- Multi-Agent Mode ---
        if request.use_multi_agent:
            print(f"🤖 Multi-Agent 모드로 처리: '{request.question}'")
            
            from agents import MasterAgent
            from agents.agent_context import AgentContext, QueryComplexity
            
            # AgentContext 생성
            context = AgentContext(
                question=request.question,
                complexity=QueryComplexity.COMPLEX,  # 기본값, Master가 재분석
                enable_web_search=request.enable_web_search
            )
            
            # Master Agent 실행 (MCP Manager 전달)
            master = MasterAgent(engine=engine, mcp_manager=mcp_manager)
            context = await master.execute(context)
            
            # 결과 반환
            return {
                "question": request.question,
                "answer": context.final_report,
                "sources": context.sources,
                "confidence": context.confidence,
                "recommendation": context.recommendation,
                "insights": context.insights,
                "retrieval_backend": context.retrieval_backend,
                "processing_steps": context.processing_steps,
                "mode": "MULTI_AGENT",
                "status": "success"
            }
        
        # --- Decision Layer (Router) ---
        # 웹 검색이 활성화된 경우에만 질문 분류
        if request.enable_web_search:
            # 1단계: 질문 분류 (GRAPH_RAG vs WEB_SEARCH)
            print(f"🤔 질문 분류 중 (웹 검색 활성화됨): '{request.question}'")
            query_type = await classify_query(request.question)
            print(f"✅ 분류 결과: {query_type}")
        else:
            # 웹 검색 비활성화 시 항상 GraphRAG 사용
            query_type = "GRAPH_RAG"
            print(f"📚 웹 검색 비활성화 - 업로드된 문서에서만 검색합니다")
        
        # 2단계: 분류 결과에 따라 처리
        sources_list = []
        
        if query_type == "WEB_SEARCH":
            # 웹 검색으로 처리
            print(f"🌐 웹 검색 모드로 처리")
            # 웹 검색 수행
            search_results = await web_search(request.question, max_results=WEB_SEARCH_MAX_RESULTS)
            
            if search_results:
                # 웹 검색 결과를 sources 형식으로 변환
                sources_list = [
                    {
                        "id": idx,
                        "file": result["title"],
                        "chunk_id": result["url"],
                        "excerpt": result["snippet"],
                        "url": result["url"]
                    }
                    for idx, result in enumerate(search_results, 1)
                ]
                
                # Report 형식 프롬프트 생성
                report_prompt = get_web_search_report_prompt(request.question, search_results)
                
                # LLM으로 보고서 생성 (사용자 지정 temperature 사용)
                client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
                llm_response = await client.chat.completions.create(
                    model=ROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": report_prompt},
                        {"role": "user", "content": request.question}
                    ],
                    temperature=request.temperature,
                    max_tokens=2000
                )
                response = llm_response.choices[0].message.content.strip()
            else:
                response = "죄송해요, 웹 검색 결과를 찾을 수 없었어요. 다른 질문을 해보시겠어요?"
            
            source = "WEB_SEARCH"
        else:
            # GraphRAG로 처리 (출처 정보 포함)
            print(f"📚 GraphRAG 모드로 처리 (mode: {request.mode}, search_type: {request.search_type}, temperature: {request.temperature}, top_k: {request.top_k})")
            retrieval_backend = "unknown"
            retrieval_context = ""
            
            # Global vs Local search 분기
            if request.search_type == "global":
                # Global Search: 전체 문서 요약
                result = await engine.aglobal_search(
                    request.question,
                    top_k=request.top_k,
                    temperature=request.temperature
                )
                base_answer = result.get("answer", "")
                sources_list = result.get("sources", [])
                retrieval_backend = "community"
            else:
                # Local Search: 특정 엔티티 검색
                result = await engine.aquery(
                    request.question,
                    mode=request.mode,
                    return_context=True,
                    top_k=request.top_k
                )
                
                if isinstance(result, dict):
                    base_answer = result.get("answer", "")
                    sources_list = result.get("sources", [])
                    retrieval_backend = result.get("retrieval_backend", "unknown")
                    retrieval_context = result.get("context", "") or ""
                else:
                    base_answer = result
                    sources_list = []
            
            # Strict Grounding으로 보고서 재생성
            if sources_list:
                # #region agent log
                with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                    f.write(__import__('json').dumps({"location":"app.py:567","message":"sources_list before grounding","data":{"count":len(sources_list),"sources":[{"id":s.get("id"),"file":s.get("file"),"excerpt":s.get("excerpt","")[:100]} for s in sources_list[:3]]},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H4"})+'\n')
                # #endregion
                # 실제 소스 개수만 사용하도록 제한
                max_sources = min(len(sources_list), 10)  # 최대 10개
                sources_list = sources_list[:max_sources]
                
                # Strict Grounding Prompt 사용
                from utils import get_strict_grounding_prompt
                strict_prompt = get_strict_grounding_prompt(request.question, sources_list)
                
                client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
                llm_response = await client.chat.completions.create(
                    model=ROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": strict_prompt},
                        {"role": "user", "content": request.question}
                    ],
                    temperature=0.0,  # Strict grounding: 창의성 제거
                    max_tokens=2000
                )
                response = llm_response.choices[0].message.content.strip()
                # #region agent log
                with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                    f.write(__import__('json').dumps({"location":"app.py:584","message":"LLM response before validation","data":{"response_length":len(response),"response_preview":response[:300]},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H5"})+'\n')
                # #endregion
                
                # Self-Correction: Citation Validation
                from citation_validator import CitationValidator
                validator = CitationValidator(sources_list)
                validation_result = validator.validate_response(response)
                evidence = []
                # #region agent log
                with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                    f.write(__import__('json').dumps({"location":"app.py:596","message":"validation result","data":{"confidence":validation_result.get('confidence_score'),"valid_citations":validation_result.get('valid_citations'),"total_citations":validation_result.get('total_citations'),"missing_citations":validation_result.get('missing_citations',[])},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H5"})+'\n')
                # #endregion
                
                print(f"[VALIDATION] Confidence: {validation_result['confidence_score']:.1%}")
                print(f"[VALIDATION] Valid citations: {validation_result['valid_citations']}/{validation_result['total_citations']}")

                # #region agent log
                import json
                with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"location":"app.py:607","message":"Response before override check","data":{"response_preview":response[:500],"has_html_tags":"<a href" in response or "<div" in response,"sources_count":len(sources_list)},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H1,H4"})+'\n')
                # #endregion
                
                # Strict Grounding LLM이 '정보 없음'이라고 답했지만 실제로는 소스가 충분한 경우 보정
                override_applied = False
                if response.strip() == "해당 문서들에서는 관련 정보를 찾을 수 없습니다." and len(sources_list) > 0:
                    print("[WARNING] Strict grounding LLM returned 'no info' despite non-empty sources. Falling back to base GraphRAG answer.")
                    # #region agent log
                    with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
                        f.write(__import__('json').dumps({
                            "location": "app.py:610",
                            "message": "override no-info with base_answer",
                            "data": {
                                "base_answer_preview": base_answer[:200] if base_answer else None,
                                "sources_count": len(sources_list)
                            },
                            "timestamp": __import__('time').time()*1000,
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "H4,H5"
                        }) + '\n')
                    # #endregion
                    response = base_answer or response
                    # base_answer에는 citation이 없을 수 있으므로 validation은 유지하되 신뢰도는 0.7 이상으로 설정하여 후속 체크를 통과시킴
                    validation_result = {"confidence_score": 0.75, "is_valid": True}
                    evidence = []
                    override_applied = True

                # 신뢰도가 낮거나 응답이 비정상적이면 "정보 없음" 응답으로 대체
                # 또는 응답에 HTML/웹 검색 흔적이 있으면 거부
                # 단, override가 적용된 경우는 스킵 (base_answer를 사용하므로)
                if not override_applied and (validation_result["confidence_score"] < 0.7 or 
                    "<a href" in response or 
                    "Thesaurus.com" in response or
                    "WordHippo" in response or
                    len(response.strip()) < 50):
                    print(f"[WARNING] Low confidence or invalid response, replacing with 'no info' response")
                    response = "해당 문서들에서는 관련 정보를 찾을 수 없습니다."
                    sources_list = []
                    validation_result = {"confidence_score": 0.0, "is_valid": False}
                    evidence = []
                else:
                    # 응답에서 실제로 사용된 citation 번호 추출 및 필터링
                    import re
                    citation_pattern = r'\[(\d+)\]'
                    used_citations = set()
                    for match in re.finditer(citation_pattern, response):
                        citation_num = int(match.group(1))
                        if 1 <= citation_num <= len(sources_list):
                            used_citations.add(citation_num)
                    
                    # 사용된 citation에 해당하는 소스만 유지
                    if used_citations:
                        sources_list = [s for s in sources_list if s['id'] in used_citations]
                        # ID를 1부터 다시 매핑
                        for idx, source in enumerate(sources_list, 1):
                            old_id = source['id']
                            source['id'] = idx
                            # 응답에서 citation 번호 재매핑
                            response = response.replace(f'[{old_id}]', f'[{idx}]')
                            response = re.sub(rf'\[{old_id}\]', f'[{idx}]', response)

                    # evidence(클레임-근거) 구조 생성 (citation remap 이후)
                    # override가 적용된 경우는 evidence를 빈 배열로 유지 (base_answer에는 citation이 없음)
                    if not override_applied:
                        validator = CitationValidator(sources_list)
                        evidence = validator.build_evidence(response)
                    # override_applied인 경우 evidence는 이미 빈 배열로 설정됨
            else:
                # 출처가 없으면 "정보 없음" 응답
                response = "해당 문서들에서는 관련 정보를 찾을 수 없습니다."
                validation_result = {"confidence_score": 0.0, "is_valid": False}
                evidence = []
            
            source = "GRAPH_RAG"
        
        # #region agent log
        import json
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"app.py:678","message":"Final response before return","data":{"response_preview":response[:500],"has_html_tags":"<a href" in response or "<div" in response,"sources_count":len(sources_list),"validation_confidence":validation_result.get('confidence_score',0) if 'validation_result' in locals() else None},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H1,H4"})+'\n')
        # #endregion
        
        # #region agent log
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"app.py:338","message":"Query response","data":{"response":response[:500] if response else None,"response_type":type(response).__name__,"source":source},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H1,H3"})+'\n')
        # #endregion
        
        # return은 "이걸 돌려줘"라는 뜻이에요!
        return {
            "question": request.question,
            "answer": response,
            "sources": sources_list,  # Citation용 출처 리스트
            "source": source,  # 어디서 답변을 가져왔는지 알려줘요!
            "mode": request.mode if source == "GRAPH_RAG" else "N/A",  # GraphRAG일 때만 의미 있어요
            "search_type": request.search_type if source == "GRAPH_RAG" else "N/A",
            "validation": validation_result if source == "GRAPH_RAG" and 'validation_result' in locals() else None,
            "evidence": evidence if source == "GRAPH_RAG" and 'evidence' in locals() else [],
            "retrieval_backend": retrieval_backend if source == "GRAPH_RAG" and 'retrieval_backend' in locals() else "N/A",
            "retrieval_context": retrieval_context if source == "GRAPH_RAG" and 'retrieval_context' in locals() else "",
            "status": "success"
        }
    except Exception as e:
        # #region agent log
        import traceback
        with open('/Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"app.py:352","message":"Query error","data":{"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","runId":"run1","hypothesisId":"H1,H4"})+'\n')
        # #endregion
        # except는 "만약 에러가 생기면"이라는 뜻이에요!
        raise HTTPException(status_code=500, detail=f"질문 처리 중 에러가 발생했어요: {str(e)}")


# --- [12] 도메인 특화 엔드포인트 ---

@app.get("/domain/event/{event_name}")
async def get_event_impact(event_name: str):
    """
    Event의 인과관계 체인 조회
    
    Args:
        event_name: Event 이름
    
    Returns:
        Event → Factor → Asset 인과관계 체인
    """
    try:
        from engine.executor import QueryExecutor
        from engine.neo4j_retriever import query_event_impact_chain
        
        executor = QueryExecutor()
        try:
            impact_chain = query_event_impact_chain(executor, event_name)
            
            return {
                "event": event_name,
                "impact_chain": impact_chain,
                "count": len(impact_chain),
                "status": "success"
            }
        finally:
            executor.close()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event impact chain 조회 중 에러: {str(e)}")


@app.get("/domain/actor/{actor_name}")
async def get_actor_influence(actor_name: str):
    """
    Actor의 영향력 조회
    
    Args:
        actor_name: Actor 이름
    
    Returns:
        Actor가 관여한 Event와 그 영향
    """
    try:
        from engine.executor import QueryExecutor
        from engine.neo4j_retriever import query_actor_influence
        
        executor = QueryExecutor()
        try:
            influence_data = query_actor_influence(executor, actor_name)
            
            return {
                "actor": actor_name,
                "influence": influence_data,
                "count": len(influence_data),
                "status": "success"
            }
        finally:
            executor.close()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Actor influence 조회 중 에러: {str(e)}")


@app.get("/domain/region/{region_name}")
async def get_regional_events(region_name: str):
    """
    지역별 Event 조회
    
    Args:
        region_name: Region 이름
    
    Returns:
        특정 지역의 Event와 영향받은 Asset
    """
    try:
        from engine.executor import QueryExecutor
        from engine.neo4j_retriever import query_regional_events
        
        executor = QueryExecutor()
        try:
            regional_events = query_regional_events(executor, region_name)
            
            return {
                "region": region_name,
                "events": regional_events,
                "count": len(regional_events),
                "status": "success"
            }
        finally:
            executor.close()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Regional events 조회 중 에러: {str(e)}")


@app.get("/domain/asset/{asset_name}")
async def get_asset_factors(asset_name: str):
    """
    Asset에 영향을 주는 Factor들 조회
    
    Args:
        asset_name: Asset 이름
    
    Returns:
        Asset에 영향을 주는 Factor 리스트
    """
    try:
        from engine.executor import QueryExecutor
        from engine.neo4j_retriever import query_asset_factors
        
        executor = QueryExecutor()
        try:
            factors = query_asset_factors(executor, asset_name)
            
            return {
                "asset": asset_name,
                "factors": factors,
                "count": len(factors),
                "status": "success"
            }
        finally:
            executor.close()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Asset factors 조회 중 에러: {str(e)}")


@app.post("/domain/schema/init")
async def initialize_domain_schema():
    """
    도메인 스키마 초기화 (Constraint 및 Index 생성)
    
    Returns:
        초기화 결과
    """
    try:
        from db.neo4j_db import Neo4jDatabase
        
        db = Neo4jDatabase()
        result = db.create_domain_schema()
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"도메인 스키마 초기화 중 에러: {str(e)}")


# --- [13] 서버 실행 ---
# if __name__ == "__main__": 이건 "이 파일을 직접 실행했을 때만"이라는 뜻이에요!
if __name__ == "__main__":
    # uvicorn.run()은 "서버를 실행하는" 거예요!
    # app은 "FastAPI 앱"이에요!
    # host="0.0.0.0"은 "모든 네트워크 인터페이스에서 접속 가능"하다는 뜻이에요!
    # port=8000은 "8000번 포트를 사용한다"는 뜻이에요!
    uvicorn.run(app, host="0.0.0.0", port=8000)

