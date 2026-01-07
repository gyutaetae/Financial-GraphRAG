# config.py는 "설정 파일"이에요!
# 마치 "이 프로젝트를 어떻게 사용할지 정하는 설명서" 같은 거예요!

import os
from typing import Literal
# dotenv는 .env 파일을 읽어서 환경변수로 설정해주는 도구예요!
# 마치 "설정 파일을 읽어서 환경변수로 만들어주는" 것처럼!
try:
    from dotenv import load_dotenv
    # load_dotenv()는 .env 파일을 읽어서 환경변수로 설정해요!
    load_dotenv()
except ImportError:
    # dotenv가 없으면 그냥 넘어가요!
    pass

# --- [1] 실행 모드 설정 ---
# RUN_MODE는 "어떤 모드로 실행할지" 정하는 거예요!
# "API"는 OpenAI API를 사용한다는 뜻이에요!
# "LOCAL"은 Ollama 로컬 모델을 사용한다는 뜻이에요!
# Literal은 "이 값들 중 하나만 선택할 수 있어요"라는 뜻이에요!
RUN_MODE: Literal["API", "LOCAL"] = os.getenv("RUN_MODE", "API")

# --- [2] OpenAI API 설정 ---
# OpenAI API 키를 환경변수에서 가져와요!
# os.getenv()는 "환경변수에서 값을 가져와"라는 뜻이에요!
# 마치 "비밀번호를 환경변수에서 가져와"라는 것처럼!
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# OpenAI API 베이스 URL (기본값 사용)
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# --- [3] 모델 설정 ---
# API 모드일 때 사용할 모델들
API_MODELS = {
    # LLM 모델: gpt-4o-mini는 OpenAI의 작고 빠른 모델이에요!
    # 인덱싱(공부)할 때는 정확한 금융 수치를 추출하기 위해 이 모델을 써요!
    "llm": "gpt-4o-mini",
    # Embedding 모델: text-embedding-3-small은 텍스트를 벡터로 바꾸는 모델이에요!
    "embedding": "text-embedding-3-small",
    # Embedding 차원: text-embedding-3-small은 1536차원 벡터를 만들어요!
    "embedding_dim": 1536,
}

# LOCAL 모드일 때 사용할 모델들
LOCAL_MODELS = {
    # LLM 모델: llama3.2:3b는 Ollama의 작은 모델이에요!
    "llm": "llama3.2:3b",
    # Embedding 모델: nomic-embed-text는 Ollama의 임베딩 모델이에요!
    "embedding": "nomic-embed-text",
    # Embedding 차원: nomic-embed-text는 768차원 벡터를 만들어요!
    "embedding_dim": 768,
}

# --- [4] GraphRAG 작업 디렉토리 설정 ---
# working_dir은 "그래프 데이터를 저장할 폴더"예요!
# macOS에서 권한 문제(Errno 1: Operation not permitted)가 날 수 있어서
# 기본값을 사용자 쓰기 가능한 /tmp 하위로 변경해요.
WORKING_DIR = os.getenv("GRAPH_WORKING_DIR", "/tmp/graph_storage_hybrid")

# --- [4-1] 개발 모드 설정 (빠른 테스트용) ---
# DEV_MODE가 True면 텍스트 앞부분만 사용해서 빠르게 테스트해요!
# 환경변수 DEV_MODE=true 또는 DEV_MODE=1로 설정하면 활성화돼요!
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
DEV_MODE_MAX_CHARS = int(os.getenv("DEV_MODE_MAX_CHARS", "5000"))  # 개발 모드일 때 최대 글자 수

# --- [4-2] Neo4j 연결 설정 ---
# Neo4j 데이터베이스에 연결하기 위한 설정들이에요!
# NEO4J_AUTO_EXPORT가 True면 인덱싱 후 자동으로 Neo4j에 업로드해요!
NEO4J_URI = os.getenv("NEO4J_URI", "")  # Neo4j 접속 주소 (예: neo4j+s://xxxxx.databases.neo4j.io)
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")  # Neo4j 사용자 이름
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")  # Neo4j 비밀번호
NEO4J_AUTO_EXPORT = os.getenv("NEO4J_AUTO_EXPORT", "false").lower() in ("true", "1", "yes")  # 자동 업로드 여부

# --- [5] 금융 특화 설정 ---
# FINANCIAL_ENTITY_TYPES는 "금융에서 중요한 엔티티 타입들"이에요!
# 이 타입들을 우선적으로 추출하도록 설정해요!
FINANCIAL_ENTITY_TYPES = [
    "REVENUE",           # 매출
    "OPERATING_INCOME",  # 영업이익
    "NET_INCOME",        # 순이익
    "GROWTH_RATE",       # 성장률
    "MARGIN",            # 마진
    "ASSET",             # 자산
    "LIABILITY",         # 부채
    "EQUITY",            # 자본
    "CASH_FLOW",         # 현금흐름
    "EPS",               # 주당순이익
    "PE_RATIO",          # 주가수익비율
    "MARKET_CAP",        # 시가총액
]

# --- [6] 현재 모드에 맞는 모델 설정 가져오기 ---
# get_models()는 "현재 모드에 맞는 모델 설정을 가져오는" 함수예요!
def get_models():
    # if는 "만약"이라는 뜻이에요!
    if RUN_MODE == "API":
        # API 모드면 API_MODELS를 반환해요!
        return API_MODELS
    else:
        # LOCAL 모드면 LOCAL_MODELS를 반환해요!
        return LOCAL_MODELS

# --- [7] 설정 검증 ---
# validate_config()는 "설정이 올바른지 확인하는" 함수예요!
def validate_config():
    # API 모드인데 API 키가 없으면 에러를 발생시켜요!
    if RUN_MODE == "API" and not OPENAI_API_KEY:
        raise ValueError(
            "❌ API 모드를 사용하려면 OPENAI_API_KEY 환경변수를 설정해주세요!\n"
            "💡 예시: export OPENAI_API_KEY='sk-...'"
        )
    return True

# --- [8] 설정 정보 출력 ---
# print_config()는 "현재 설정을 보여주는" 함수예요!
def print_config():
    models = get_models()
    print("=" * 50)
    print("📋 VIK AI Hybrid GraphRAG 설정")
    print("=" * 50)
    print(f"🔧 실행 모드: {RUN_MODE}")
    print(f"📁 작업 디렉토리: {WORKING_DIR}")
    print(f"🤖 LLM 모델: {models['llm']}")
    print(f"🔢 Embedding 모델: {models['embedding']}")
    print(f"📏 Embedding 차원: {models['embedding_dim']}")
    if RUN_MODE == "API":
        print(f"🔑 OpenAI API 키: {'✅ 설정됨' if OPENAI_API_KEY else '❌ 없음'}")
    print(f"🗄️  Neo4j 자동 업로드: {'✅ 활성화' if NEO4J_AUTO_EXPORT else '❌ 비활성화'}")
    if NEO4J_AUTO_EXPORT:
        print(f"🔗 Neo4j URI: {'✅ 설정됨' if NEO4J_URI else '❌ 없음'}")
    print("=" * 50)

