"""
Configuration module for Finance GraphRAG
Manages environment variables and model settings with strict typing
"""

import os
from typing import Literal, Dict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Runtime mode: API (OpenAI) or LOCAL (Ollama)
RUN_MODE: Literal["API", "LOCAL"] = os.getenv("RUN_MODE", "API")  # type: ignore

# OpenAI API Configuration
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Ollama Configuration (하이브리드 클라우드 지원)
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Model configurations with strict typing
API_MODELS: Dict[str, str | int] = {
    "llm": "gpt-4o-mini",  # Fast, cost-effective for financial analysis
    "embedding": "text-embedding-3-small",
    "embedding_dim": 1536,
}

LOCAL_MODELS: Dict[str, str | int] = {
    "llm": "qwen2.5-coder:3b",  # Privacy-first, code-optimized
    "embedding": "nomic-embed-text",
    "embedding_dim": 768,
}

# GraphRAG working directory (writable location to prevent permission issues)
WORKING_DIR: str = os.getenv("GRAPH_WORKING_DIR", "/tmp/graph_storage_hybrid")

# Development mode (limits text size for faster testing)
DEV_MODE: bool = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
DEV_MODE_MAX_CHARS: int = int(os.getenv("DEV_MODE_MAX_CHARS", "5000"))

# Neo4j database configuration
NEO4J_URI: str = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
NEO4J_AUTO_EXPORT: bool = os.getenv("NEO4J_AUTO_EXPORT", "false").lower() in ("true", "1", "yes")

# Financial entity types for prioritized extraction
FINANCIAL_ENTITY_TYPES: list[str] = [
    "REVENUE", "OPERATING_INCOME", "NET_INCOME", "GROWTH_RATE",
    "MARGIN", "ASSET", "LIABILITY", "EQUITY", "CASH_FLOW",
    "EPS", "PE_RATIO", "MARKET_CAP",
]

# Router configuration for query classification
ROUTER_MODEL: str = "gpt-4o-mini"
ROUTER_TEMPERATURE: float = 0.0  # Deterministic routing
WEB_SEARCH_MAX_RESULTS: int = 5

# MCP (Multi-Context Protocol) server configuration
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
MCP_CONFIG_PATH: str = os.getenv("MCP_CONFIG_PATH", "mcp-config.json")
MCP_LAZY_LOAD: bool = os.getenv("MCP_LAZY_LOAD", "true").lower() in ("true", "1", "yes")

# Domain schema configuration (Event-Actor-Asset-Factor-Region)
ENABLE_DOMAIN_SCHEMA: bool = os.getenv("ENABLE_DOMAIN_SCHEMA", "true").lower() in ("true", "1", "yes")
DOMAIN_CLASSIFICATION_MODEL: str = os.getenv("DOMAIN_CLASSIFICATION_MODEL", "gpt-4o-mini")


def get_models() -> Dict[str, str | int]:
    """Return model configuration based on current RUN_MODE"""
    return API_MODELS if RUN_MODE == "API" else LOCAL_MODELS

def validate_config() -> bool:
    """
    Validate configuration settings
    Raises ValueError for critical missing configurations
    """
    if RUN_MODE == "API" and not OPENAI_API_KEY:
        raise ValueError(
            "API mode requires OPENAI_API_KEY. "
            "Set it in .env: OPENAI_API_KEY='sk-...'"
        )
    
    # Non-critical warnings
    if not TAVILY_API_KEY:
        print("⚠️  TAVILY_API_KEY not set. Tavily Search unavailable.")
        print("💡 Get key at: https://tavily.com/")
    
    return True


def print_config() -> None:
    """Display current configuration settings"""
    models = get_models()
    print("=" * 50)
    print("📋 VIK AI Hybrid GraphRAG Configuration")
    print("=" * 50)
    print(f"🔧 Mode: {RUN_MODE}")
    print(f"📁 Working Dir: {WORKING_DIR}")
    print(f"🤖 LLM: {models['llm']}")
    print(f"🔢 Embedding: {models['embedding']} (dim: {models['embedding_dim']})")
    if RUN_MODE == "API":
        print(f"🔑 OpenAI API: {'✅' if OPENAI_API_KEY else '❌'}")
    print(f"🗄️  Neo4j Auto Export: {'✅' if NEO4J_AUTO_EXPORT else '❌'}")
    if NEO4J_AUTO_EXPORT:
        print(f"🔗 Neo4j URI: {'✅' if NEO4J_URI else '❌'}")
    print(f"🔌 MCP Lazy Load: {'✅' if MCP_LAZY_LOAD else '❌'}")
    print(f"🔍 Tavily API: {'✅' if TAVILY_API_KEY else '❌'}")
    print(f"🏗️  Domain Schema: {'✅' if ENABLE_DOMAIN_SCHEMA else '❌'}")
    if ENABLE_DOMAIN_SCHEMA:
        print(f"🤖 Classification Model: {DOMAIN_CLASSIFICATION_MODEL}")
    print("=" * 50)

