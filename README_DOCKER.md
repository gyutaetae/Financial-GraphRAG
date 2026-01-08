# Docker Quick Start Guide

## 빠른 시작 (3단계)

### 1단계: 환경 설정

```bash
# env.example을 .env로 복사
cp env.example .env

# .env 파일 편집
nano .env
```

필수 설정:
```bash
OPENAI_API_KEY=sk-your-key-here
NEO4J_PASSWORD=your_secure_password
RUN_MODE=API
```

### 2단계: Docker 실행

```bash
# 모든 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### 3단계: 접속

- **Streamlit UI**: http://localhost:8501
- **FastAPI API**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474

## 주요 명령어

```bash
# 서비스 시작
docker-compose up -d

# 서비스 중지
docker-compose down

# 로그 보기
docker-compose logs -f backend
docker-compose logs -f frontend

# 서비스 재시작
docker-compose restart backend

# 상태 확인
docker-compose ps
```

## LOCAL 모드 (Ollama) 사용

```bash
# .env 파일에서 설정
RUN_MODE=LOCAL

# Ollama 컨테이너에서 모델 다운로드
docker exec -it finance-graphrag-ollama ollama pull llama3.2:3b
docker exec -it finance-graphrag-ollama ollama pull nomic-embed-text

# 서비스 재시작
docker-compose restart backend
```

## 문제 해결

### 포트 충돌

```bash
# 이미 사용 중인 포트 확인
lsof -i :8000
lsof -i :8501
lsof -i :7687

# 프로세스 종료
kill -9 <PID>
```

### Neo4j 연결 실패

```bash
# Neo4j 상태 확인
docker exec -it finance-graphrag-neo4j cypher-shell -u neo4j -p your_password_here

# .env 파일의 비밀번호와 docker-compose.yml의 비밀번호가 일치하는지 확인
```

### 메모리 부족

```bash
# Docker Desktop에서 메모리 할당 늘리기 (최소 8GB 권장)
# Settings > Resources > Memory
```

## 데이터 백업

```bash
# GraphRAG 저장소 백업
tar -czf storage_backup_$(date +%Y%m%d).tar.gz storage/

# Neo4j 백업
docker exec finance-graphrag-neo4j neo4j-admin database dump neo4j --to-path=/backups
docker cp finance-graphrag-neo4j:/backups ./neo4j_backups
```

## 전체 정리

```bash
# 컨테이너 중지 및 삭제
docker-compose down

# 볼륨까지 삭제 (주의: 모든 데이터 삭제)
docker-compose down -v

# 이미지까지 삭제
docker-compose down --rmi all
```

## 자세한 문서

전체 문서는 `DOCKER_SETUP.md`를 참조하세요.

