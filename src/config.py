"""
Configuration module for Finance GraphRAG
Manages environment variables and model settings with strict typing
"""

import os
from typing import Literal, Dict, Any

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

# Privacy Mode Configuration (8GB RAM optimized, offline-first)
PRIVACY_MODE: bool = os.getenv("PRIVACY_MODE", "false").lower() in ("true", "1", "yes")
PRIVACY_CHUNK_SIZE: int = int(os.getenv("PRIVACY_CHUNK_SIZE", "512"))  # Smaller chunks for 8GB RAM
PRIVACY_BATCH_SIZE: int = int(os.getenv("PRIVACY_BATCH_SIZE", "5"))    # Process 5 chunks at a time
PRIVACY_MAX_MEMORY_MB: int = int(os.getenv("PRIVACY_MAX_MEMORY_MB", "2048"))  # 2GB memory limit


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


def validate_privacy_mode() -> Dict[str, Any]:
    """
    Validate Privacy Mode configuration
    
    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "details": Dict[str, Any]
        }
    """
    errors = []
    warnings = []
    details = {}
    
    # Check required settings
    if not NEO4J_URI:
        errors.append("NEO4J_URI not set in .env")
        details["neo4j_uri"] = None
    else:
        details["neo4j_uri"] = NEO4J_URI
    
    if not NEO4J_PASSWORD:
        errors.append("NEO4J_PASSWORD not set in .env")
        details["neo4j_password"] = False
    else:
        details["neo4j_password"] = True
    
    if not NEO4J_USERNAME:
        warnings.append("NEO4J_USERNAME not set, using default 'neo4j'")
        details["neo4j_username"] = "neo4j (default)"
    else:
        details["neo4j_username"] = NEO4J_USERNAME
    
    # Check Ollama availability
    try:
        import requests
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            details["ollama_status"] = "running"
            details["ollama_models"] = model_names
            
            # Check if required model is available
            required_model = LOCAL_MODELS.get("llm", "qwen2.5-coder:3b")
            if not any(required_model in name for name in model_names):
                warnings.append(f"Required model '{required_model}' not found in Ollama")
                warnings.append(f"Run: ollama pull {required_model}")
        else:
            errors.append(f"Ollama server returned status {response.status_code}")
            details["ollama_status"] = f"error_{response.status_code}"
    except requests.exceptions.ConnectionError:
        errors.append(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}")
        errors.append("Run: ollama serve")
        details["ollama_status"] = "not_running"
    except Exception as e:
        warnings.append(f"Ollama check failed: {e}")
        details["ollama_status"] = "unknown"
    
    # Check Python dependencies
    try:
        import neo4j
        details["neo4j_driver"] = "installed"
    except ImportError:
        errors.append("neo4j Python driver not installed")
        errors.append("Run: pip install neo4j")
        details["neo4j_driver"] = "missing"
    
    try:
        import ollama
        details["ollama_python"] = "installed"
    except ImportError:
        errors.append("ollama Python package not installed")
        errors.append("Run: pip install ollama")
        details["ollama_python"] = "missing"
    
    # Check memory settings
    if PRIVACY_MAX_MEMORY_MB > 4096:
        warnings.append(f"PRIVACY_MAX_MEMORY_MB ({PRIVACY_MAX_MEMORY_MB}MB) is high for 8GB RAM system")
    
    details["privacy_mode_enabled"] = PRIVACY_MODE
    details["privacy_chunk_size"] = PRIVACY_CHUNK_SIZE
    details["privacy_batch_size"] = PRIVACY_BATCH_SIZE
    details["privacy_max_memory_mb"] = PRIVACY_MAX_MEMORY_MB
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "details": details
    }


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
    print(f"🔒 Privacy Mode: {'✅' if PRIVACY_MODE else '❌'}")
    if PRIVACY_MODE:
        print(f"   Chunk Size: {PRIVACY_CHUNK_SIZE} | Batch: {PRIVACY_BATCH_SIZE} | Max Memory: {PRIVACY_MAX_MEMORY_MB}MB")
    print("=" * 50)

