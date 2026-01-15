# VIK AI - Privacy-First Financial GraphRAG

Enterprise-grade financial intelligence system powered by knowledge graphs.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Neo4j (Docker)
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# 3. Configure environment
cp .env.backup .env
# Edit .env with your settings

# 4. Start services
./start.sh
```

Visit: http://localhost:8501

## ✨ Features

- **Privacy-First**: Offline processing with local LLMs (Ollama)
- **Graph Intelligence**: Neo4j-powered knowledge graph
- **Multi-Agent**: Collaborative AI agents for deep analysis
- **8GB RAM Optimized**: Efficient memory management
- **Real-time Analysis**: Fast query processing with caching

## 📦 Architecture

```
src/
├── agents/          # Multi-agent system (Analyst, Planner, Writer)
├── engine/          # Graph processing engine
│   ├── extractor.py       # Entity/Relationship extraction
│   ├── translator.py      # JSON → Cypher
│   ├── graphrag_engine.py # Core engine
│   └── privacy_graph_builder.py # Privacy-optimized builder
├── db/              # Neo4j integration
├── mcp/             # External tool integration
└── streamlit_app.py # Web UI
```

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# Mode
RUN_MODE=API              # API (OpenAI) or LOCAL (Ollama)
PRIVACY_MODE=true         # Enable privacy-first mode

# OpenAI
OPENAI_API_KEY=sk-...

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=password

# Ollama (for Privacy Mode)
OLLAMA_BASE_URL=http://localhost:11434
```

## 📊 Usage

### PDF Analysis
1. Go to "Data Ingestion" tab
2. Upload PDF document
3. System extracts entities and builds knowledge graph

### Query Interface
1. Go to "Query Interface" tab
2. Ask questions about your data
3. Get citation-backed answers with confidence scores

### Advanced Settings
- **Temperature**: Control creativity (0.0-2.0)
- **Retrieval Chunks**: Number of context chunks (5-50)
- **Web Search**: Enable real-time web data
- **Multi-Agent**: Use collaborative AI pipeline

## 🛠️ Development

```bash
# Run tests
python -m pytest tests/

# Check lints
python -m flake8 src/

# Format code
python -m black src/
```

## 📝 License

MIT License - See LICENSE file for details
