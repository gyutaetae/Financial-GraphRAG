# Docker Setup Guide for Finance GraphRAG

This guide explains how to run the Finance GraphRAG system using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- NVIDIA Docker (optional, for GPU support with Ollama)
- At least 8GB RAM available for Docker
- 20GB free disk space

## Quick Start

### 1. Environment Setup

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and set your configuration:

```bash
# Required: Set your OpenAI API key (for API mode)
OPENAI_API_KEY=sk-your-key-here

# Required: Set Neo4j password
NEO4J_PASSWORD=your_secure_password

# Optional: Choose run mode (API or LOCAL)
RUN_MODE=API
```

### 2. Start All Services

```bash
# Start all services in background
docker-compose up -d

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 3. Access the Application

- **Streamlit UI**: http://localhost:8501
- **FastAPI Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **Ollama API**: http://localhost:11434

### 4. Initial Setup

#### For LOCAL Mode (Ollama)

If using `RUN_MODE=LOCAL`, you need to pull the models first:

```bash
# Enter the Ollama container
docker exec -it finance-graphrag-ollama bash

# Pull required models
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# Exit container
exit
```

#### For API Mode (OpenAI)

No additional setup needed. Just ensure your `OPENAI_API_KEY` is set in `.env`.

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│                   (graphrag-network)                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Frontend   │  │   Backend    │  │    Neo4j     │    │
│  │  (Streamlit) │──│   (FastAPI)  │──│  (Database)  │    │
│  │   :8501      │  │    :8000     │  │ :7474/:7687  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                           │                                │
│                    ┌──────────────┐                        │
│                    │    Ollama    │                        │
│                    │   (Local LLM)│                        │
│                    │    :11434    │                        │
│                    └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Service Details

### Frontend (Streamlit)
- **Port**: 8501
- **Purpose**: User interface for querying and visualization
- **Features**:
  - Chat interface with Perplexity-style reports
  - PDF upload and indexing
  - Neo4j graph visualization
  - Advanced settings (temperature, retrieval chunks)

### Backend (FastAPI)
- **Port**: 8000
- **Purpose**: API server for GraphRAG operations
- **Endpoints**:
  - `POST /query` - Query the knowledge graph
  - `POST /insert` - Index new documents
  - `POST /reset` - Reset the graph
  - `GET /visualize` - Get graph visualization data
  - `GET /health` - Health check

### Neo4j
- **Ports**: 7474 (HTTP), 7687 (Bolt)
- **Purpose**: Graph database for storing entities and relationships
- **Credentials**: neo4j / your_password_here (change in `.env`)

### Ollama (Optional)
- **Port**: 11434
- **Purpose**: Local LLM inference (for LOCAL mode)
- **Models**: llama3.2:3b, nomic-embed-text
- **GPU**: Requires NVIDIA GPU and nvidia-docker

## Common Commands

### Start/Stop Services

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v

# Restart specific service
docker-compose restart backend
docker-compose restart frontend
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 frontend
```

### Execute Commands in Containers

```bash
# Backend shell
docker exec -it finance-graphrag-backend bash

# Frontend shell
docker exec -it finance-graphrag-frontend bash

# Neo4j Cypher shell
docker exec -it finance-graphrag-neo4j cypher-shell -u neo4j -p your_password_here

# Ollama commands
docker exec -it finance-graphrag-ollama ollama list
```

### Monitor Resources

```bash
# View resource usage
docker stats

# View container status
docker-compose ps
```

## Volume Management

Docker volumes persist data across container restarts:

- `neo4j_data`: Neo4j database files
- `neo4j_logs`: Neo4j logs
- `ollama_data`: Ollama models and cache
- `./storage`: GraphRAG storage (bind mount)
- `./logs`: Application logs (bind mount)

### Backup Data

```bash
# Backup Neo4j data
docker exec finance-graphrag-neo4j neo4j-admin database dump neo4j --to-path=/backups
docker cp finance-graphrag-neo4j:/backups ./neo4j_backups

# Backup GraphRAG storage
tar -czf storage_backup_$(date +%Y%m%d).tar.gz storage/
```

### Restore Data

```bash
# Restore Neo4j data
docker cp ./neo4j_backups/neo4j.dump finance-graphrag-neo4j:/backups/
docker exec finance-graphrag-neo4j neo4j-admin database load neo4j --from-path=/backups

# Restore GraphRAG storage
tar -xzf storage_backup_YYYYMMDD.tar.gz
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs backend

# Check if ports are already in use
lsof -i :8000
lsof -i :8501
lsof -i :7687
```

### Neo4j Connection Issues

```bash
# Check Neo4j health
docker exec finance-graphrag-neo4j cypher-shell -u neo4j -p your_password_here "RETURN 1"

# Verify credentials in .env match docker-compose.yml
grep NEO4J_PASSWORD .env
```

### Ollama Model Issues

```bash
# Check available models
docker exec finance-graphrag-ollama ollama list

# Pull missing models
docker exec finance-graphrag-ollama ollama pull llama3.2:3b
docker exec finance-graphrag-ollama ollama pull nomic-embed-text

# Test model
docker exec finance-graphrag-ollama ollama run llama3.2:3b "Hello"
```

### Out of Memory

```bash
# Increase Docker memory limit in Docker Desktop settings
# Or reduce Neo4j heap size in docker-compose.yml:
NEO4J_dbms_memory_heap_max__size=1G
```

### Permission Issues

```bash
# Fix volume permissions
sudo chown -R $USER:$USER storage/ logs/

# Or run with proper user in docker-compose.yml:
user: "${UID}:${GID}"
```

## Development Mode

For development with hot-reload:

```bash
# Backend with auto-reload
docker-compose up backend

# Frontend with auto-reload (already enabled)
docker-compose up frontend
```

Changes to `src/` files will automatically reload the services.

## Production Deployment

For production, create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    command: uvicorn src.app:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      - LOG_LEVEL=WARNING
    restart: always

  frontend:
    environment:
      - STREAMLIT_SERVER_HEADLESS=true
    restart: always
```

Run with:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## GPU Support (for Ollama)

To use GPU with Ollama:

1. Install NVIDIA Docker:
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

2. Verify GPU access:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

3. Start services:
```bash
docker-compose up -d
```

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Full cleanup
docker system prune -a --volumes
```

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- GitHub Issues: [Your Repo URL]
- Documentation: README.md, ROUTER_IMPLEMENTATION.md

