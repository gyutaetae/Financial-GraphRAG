# Docker 설정 가이드

## 📋 사전 요구사항

1. **Docker Desktop 설치**
   - macOS: https://www.docker.com/products/docker-desktop/
   - Windows: https://www.docker.com/products/docker-desktop/
   - Linux: `sudo apt-get install docker.io docker-compose`

2. **Docker 실행 확인**
   ```bash
   docker --version
   docker-compose --version
   ```

## 🚀 빠른 시작

### 1단계: 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성:

```bash
# .env 파일 생성
cat > .env << EOF
# OpenAI API 설정
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# Neo4j 비밀번호 설정
NEO4J_PASSWORD=your_secure_password_here

# 실행 모드 (API: OpenAI 사용, LOCAL: Ollama 사용)
RUN_MODE=API

# 선택사항: Ollama 사용 시
OLLAMA_BASE_URL=http://ollama:11434
EOF
```

**중요:** `.env` 파일은 절대 Git에 커밋하지 마세요! (이미 .gitignore에 포함됨)

### 2단계: Docker 이미지 빌드 및 실행

```bash
# 프로젝트 디렉토리로 이동
cd /Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG

# Docker Compose로 모든 서비스 시작
docker-compose up --build -d

# 또는 백그라운드 없이 로그 보면서 실행
docker-compose up --build
```

### 3단계: 서비스 확인

**서비스 접속 주소:**
- **Streamlit UI**: http://localhost:8501
- **FastAPI Backend**: http://localhost:8000
- **Neo4j Browser**: http://localhost:7474
- **Ollama API**: http://localhost:11434

**서비스 상태 확인:**
```bash
# 모든 컨테이너 상태 확인
docker-compose ps

# 특정 서비스 로그 확인
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f neo4j
```

## 🔧 상세 설정

### Neo4j 초기 설정

1. **Neo4j Browser 접속**
   - URL: http://localhost:7474
   - 초기 로그인:
     - Username: `neo4j`
     - Password: `.env` 파일에 설정한 `NEO4J_PASSWORD`

2. **비밀번호 변경** (첫 로그인 시 필수)
   - Neo4j Browser에서 비밀번호 변경 프롬프트가 나타나면 새 비밀번호 입력
   - `.env` 파일의 `NEO4J_PASSWORD`도 동일하게 업데이트

### 서비스별 설정

#### 1. FastAPI Backend (backend)

**환경 변수:**
- `RUN_MODE`: `API` (OpenAI) 또는 `LOCAL` (Ollama)
- `OPENAI_API_KEY`: OpenAI API 키
- `NEO4J_URI`: `bolt://neo4j:7687` (자동 설정)
- `OLLAMA_BASE_URL`: `http://ollama:11434` (자동 설정)

**포트:** 8000

#### 2. Streamlit Frontend (frontend)

**환경 변수:**
- `API_BASE_URL`: `http://backend:8000` (자동 설정)
- `NEO4J_URI`: `bolt://neo4j:7687` (자동 설정)

**포트:** 8501

#### 3. Neo4j Database (neo4j)

**포트:**
- HTTP: 7474
- Bolt: 7687

**볼륨:** 데이터는 `neo4j_data` 볼륨에 영구 저장

#### 4. Ollama (ollama) - 선택사항

**포트:** 11434

**GPU 지원:** NVIDIA GPU가 있는 경우 자동으로 사용

## 📝 일반적인 명령어

### 서비스 관리

```bash
# 모든 서비스 시작
docker-compose up -d

# 모든 서비스 중지
docker-compose down

# 모든 서비스 중지 + 볼륨 삭제 (데이터 삭제됨!)
docker-compose down -v

# 특정 서비스만 재시작
docker-compose restart backend
docker-compose restart frontend

# 이미지 재빌드
docker-compose build --no-cache

# 로그 실시간 확인
docker-compose logs -f

# 특정 서비스 로그만
docker-compose logs -f frontend
```

### 컨테이너 내부 접속

```bash
# Backend 컨테이너 접속
docker exec -it finance-graphrag-backend bash

# Frontend 컨테이너 접속
docker exec -it finance-graphrag-frontend bash

# Neo4j 컨테이너 접속
docker exec -it finance-graphrag-neo4j bash
```

### 데이터 백업

```bash
# Neo4j 데이터 백업
docker exec finance-graphrag-neo4j neo4j-admin dump --database=neo4j --to=/var/lib/neo4j/import/backup.dump

# 볼륨 백업
docker run --rm -v finance-graphrag_neo4j_data:/data -v $(pwd):/backup alpine tar czf /backup/neo4j_backup.tar.gz /data
```

## 🐛 문제 해결

### 1. 포트 충돌

**증상:** `port is already allocated` 오류

**해결:**
```bash
# 사용 중인 포트 확인
lsof -i :8000
lsof -i :8501
lsof -i :7474

# docker-compose.yml에서 포트 변경
# 예: "8502:8501" (호스트:컨테이너)
```

### 2. Connection Refused

**증상:** Streamlit에서 FastAPI 연결 실패

**확인 사항:**
```bash
# Backend가 실행 중인지 확인
docker-compose ps backend

# Backend 로그 확인
docker-compose logs backend

# 네트워크 확인
docker network inspect finance-graphrag_graphrag-network
```

### 3. Neo4j 연결 실패

**증상:** `Connection refused` 또는 `Authentication failed`

**해결:**
1. Neo4j Browser에서 비밀번호 확인
2. `.env` 파일의 `NEO4J_PASSWORD` 확인
3. Neo4j 컨테이너 재시작:
   ```bash
   docker-compose restart neo4j
   ```

### 4. 메모리 부족

**증상:** 컨테이너가 자주 재시작됨

**해결:**
- `docker-compose.yml`에서 Neo4j 메모리 설정 조정:
  ```yaml
  - NEO4J_dbms_memory_heap_max__size=1G  # 2G에서 1G로 감소
  ```

### 5. 이미지 빌드 실패

**해결:**
```bash
# 캐시 없이 재빌드
docker-compose build --no-cache

# 기존 이미지 삭제 후 재빌드
docker-compose down
docker system prune -a
docker-compose up --build
```

## 🔒 보안 주의사항

1. **`.env` 파일 보호**
   - 절대 Git에 커밋하지 마세요
   - 프로덕션에서는 환경 변수 관리 시스템 사용

2. **Neo4j 비밀번호**
   - 강력한 비밀번호 사용
   - 기본 비밀번호(`your_password_here`) 반드시 변경

3. **포트 노출**
   - 프로덕션에서는 방화벽 설정
   - 필요한 포트만 외부에 노출

## 📊 리소스 사용량 확인

```bash
# 컨테이너별 리소스 사용량
docker stats

# 특정 컨테이너만
docker stats finance-graphrag-backend
```

## 🧹 정리 명령어

```bash
# 사용하지 않는 이미지/컨테이너 정리
docker system prune -a

# 볼륨 정리 (주의: 데이터 삭제됨!)
docker volume prune

# 모든 컨테이너 중지 및 삭제
docker-compose down -v --remove-orphans
```

## ✅ 체크리스트

배포 전 확인:

- [ ] Docker Desktop 실행 중
- [ ] `.env` 파일 생성 및 설정 완료
- [ ] `OPENAI_API_KEY` 설정됨
- [ ] `NEO4J_PASSWORD` 설정됨 (기본값 아님)
- [ ] 포트 충돌 없음 (8000, 8501, 7474, 7687)
- [ ] `docker-compose up --build` 성공
- [ ] 모든 서비스 정상 실행 (`docker-compose ps`)
- [ ] Streamlit UI 접속 가능 (http://localhost:8501)
- [ ] Neo4j Browser 접속 가능 (http://localhost:7474)

## 📚 추가 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Neo4j Docker 가이드](https://neo4j.com/developer/docker/)
- [Streamlit Docker 배포](https://docs.streamlit.io/knowledge-base/tutorials/deploy/docker)
