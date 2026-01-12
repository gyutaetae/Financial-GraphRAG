# Finance GraphRAG Docker 배포 가이드

## 📋 목차
1. [사전 준비](#사전-준비)
2. [환경 변수 설정](#환경-변수-설정)
3. [Docker로 배포하기](#docker로-배포하기)
4. [서비스 확인](#서비스-확인)
5. [도메인 스키마 초기화](#도메인-스키마-초기화)
6. [팀원에게 공유하기](#팀원에게-공유하기)
7. [문제 해결](#문제-해결)

---

## 1. 사전 준비

### 필요한 소프트웨어
- Docker Desktop (v20.10 이상)
- Docker Compose (v2.0 이상)

### API 키 준비
1. **OpenAI API 키**: https://platform.openai.com/api-keys
2. **Tavily Search API 키**: https://tavily.com/ (선택사항, 웹 검색 기능용)

---

## 2. 환경 변수 설정

### Step 1: `.env` 파일 생성

```bash
# env.docker.example을 .env로 복사
cp env.docker.example .env
```

### Step 2: `.env` 파일 수정

```bash
# 편집기로 .env 파일 열기
nano .env
# 또는
vim .env
```

**필수 항목 입력:**

```bash
# OpenAI API 키 (필수)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx

# Neo4j 비밀번호 (필수, 강력한 비밀번호 사용)
NEO4J_PASSWORD=YourSecurePassword123!

# Tavily API 키 (선택사항, 웹 검색 기능 사용 시)
TAVILY_API_KEY=tvly-xxxxxxxxxxxxx
```

**선택 항목 (기본값 사용 가능):**

```bash
# 도메인 스키마 활성화 (기본값: true)
ENABLE_DOMAIN_SCHEMA=true

# 분류 모델 (기본값: gpt-4o-mini)
DOMAIN_CLASSIFICATION_MODEL=gpt-4o-mini

# Neo4j 자동 업로드 (기본값: true)
NEO4J_AUTO_EXPORT=true
```

---

## 3. Docker로 배포하기

### Option A: 전체 서비스 실행 (권장)

```bash
# 모든 컨테이너 빌드 및 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f
```

**실행되는 서비스:**
- `neo4j`: Neo4j 그래프 데이터베이스 (포트 7474, 7687)
- `ollama`: Ollama 로컬 LLM 서버 (포트 11434)
- `backend`: FastAPI 백엔드 (포트 8000)
- `frontend`: Streamlit UI (포트 8501)

### Option B: 특정 서비스만 실행

```bash
# Neo4j + Backend만 실행 (UI 제외)
docker-compose up -d neo4j backend

# Frontend(Streamlit)만 재시작
docker-compose restart frontend
```

### 빌드 캐시 없이 다시 빌드

```bash
docker-compose build --no-cache
docker-compose up -d
```

---

## 4. 서비스 확인

### 4.1 컨테이너 상태 확인

```bash
docker-compose ps
```

**정상 상태:**
```
NAME                          STATUS              PORTS
finance-graphrag-neo4j        Up (healthy)        7474, 7687
finance-graphrag-ollama       Up (healthy)        11434
finance-graphrag-backend      Up                  8000
finance-graphrag-frontend     Up                  8501
```

### 4.2 Health Check

```bash
# Backend 헬스 체크
curl http://localhost:8000/health

# 응답 예시
{
  "status": "healthy",
  "message": "서버가 정상적으로 작동 중이에요!",
  "engine_ready": true
}
```

### 4.3 웹 브라우저 접속

- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
  - Username: `neo4j`
  - Password: `.env`에 설정한 `NEO4J_PASSWORD`

---

## 5. 도메인 스키마 초기화

### 5.1 API를 통한 초기화

```bash
curl -X POST http://localhost:8000/domain/schema/init
```

**응답:**
```json
{
  "status": "success",
  "message": "도메인 스키마가 성공적으로 생성되었습니다",
  "constraints": 5,
  "indexes": 10
}
```

### 5.2 Streamlit UI를 통한 초기화

1. http://localhost:8501 접속
2. "🏗️ Domain Analysis" 탭 클릭
3. 하단의 "🔧 도메인 스키마 초기화" 버튼 클릭

---

## 6. 팀원에게 공유하기

### 6.1 로컬 네트워크에서 공유

**호스트 IP 확인:**

```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

**팀원 접속 URL:**
- Streamlit UI: `http://YOUR_IP:8501`
- FastAPI: `http://YOUR_IP:8000`
- Neo4j Browser: `http://YOUR_IP:7474`

예: `http://192.168.1.100:8501`

### 6.2 클라우드 서버에 배포

#### AWS EC2 / Google Cloud VM

```bash
# 1. 서버에 Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 2. Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. 프로젝트 복사
git clone <your-repo-url>
cd Finance_GraphRAG

# 4. .env 설정
cp env.docker.example .env
nano .env  # API 키 입력

# 5. 실행
docker-compose up -d --build
```

#### 보안 그룹 / 방화벽 설정

**오픈할 포트:**
- `8501`: Streamlit UI (공개)
- `8000`: FastAPI API (공개)
- `7474`: Neo4j Browser (선택사항)
- `7687`: Neo4j Bolt (내부 통신)

### 6.3 Docker Hub에 이미지 푸시 (선택사항)

```bash
# 1. Docker Hub 로그인
docker login

# 2. 이미지 빌드 및 태그
docker build -t your-username/finance-graphrag:latest .

# 3. 푸시
docker push your-username/finance-graphrag:latest
```

**팀원이 이미지 사용:**
```bash
docker pull your-username/finance-graphrag:latest
docker run -d -p 8000:8000 --env-file .env your-username/finance-graphrag:latest
```

---

## 7. 문제 해결

### 7.1 컨테이너가 시작되지 않음

```bash
# 로그 확인
docker-compose logs backend
docker-compose logs frontend

# 컨테이너 재시작
docker-compose restart backend
```

### 7.2 포트 충돌 에러

**에러:**
```
Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```

**해결:**
```bash
# 1. 충돌하는 프로세스 찾기
lsof -i :8000

# 2. 프로세스 종료
kill -9 <PID>

# 3. 또는 docker-compose.yml에서 포트 변경
ports:
  - "8001:8000"  # 8000 → 8001
```

### 7.3 Neo4j 연결 실패

**증상:**
```
Connection refused: bolt://neo4j:7687
```

**해결:**
```bash
# 1. Neo4j 컨테이너 상태 확인
docker-compose ps neo4j

# 2. Neo4j 로그 확인
docker-compose logs neo4j

# 3. Neo4j 컨테이너만 재시작
docker-compose restart neo4j

# 4. Backend가 Neo4j를 기다리도록 depends_on 확인 (이미 설정됨)
```

### 7.4 MCP 서버 에러

**증상:**
```
MCP server startup failed
```

**해결:**
```bash
# 1. Tavily API 키 확인
echo $TAVILY_API_KEY

# 2. MCP 비활성화 (임시)
# .env 파일에서
MCP_LAZY_LOAD=false

# 3. 컨테이너 재시작
docker-compose restart backend
```

### 7.5 메모리 부족

**증상:**
```
Container killed (OOMKilled)
```

**해결:**
```bash
# docker-compose.yml에 메모리 제한 추가
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### 7.6 전체 초기화

```bash
# 모든 컨테이너 중지 및 제거
docker-compose down

# 볼륨 포함 전체 삭제 (데이터 손실 주의!)
docker-compose down -v

# 재시작
docker-compose up -d --build
```

---

## 8. 유용한 명령어

### 컨테이너 관리

```bash
# 전체 상태 확인
docker-compose ps

# 특정 컨테이너 로그
docker-compose logs -f backend

# 컨테이너 내부 접속
docker-compose exec backend bash

# 리소스 사용량 확인
docker stats
```

### 데이터 백업

```bash
# Neo4j 데이터 백업
docker-compose exec neo4j neo4j-admin dump --to=/var/lib/neo4j/import/backup.dump

# 백업 파일 복사
docker cp finance-graphrag-neo4j:/var/lib/neo4j/import/backup.dump ./backup.dump
```

### 업데이트 배포

```bash
# 1. 코드 업데이트 (git pull 등)
git pull origin main

# 2. 컨테이너 재빌드
docker-compose build --no-cache backend frontend

# 3. 재시작
docker-compose up -d backend frontend
```

---

## 9. 성능 최적화

### 9.1 Production 모드

```bash
# docker-compose.yml 수정
command: uvicorn src.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 9.2 Redis 캐싱 추가 (선택사항)

```yaml
# docker-compose.yml에 추가
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  networks:
    - graphrag-network
```

---

## 10. 보안 권장사항

1. **강력한 비밀번호 사용**
   - Neo4j 비밀번호: 최소 12자, 대소문자+숫자+특수문자

2. **API 키 보호**
   - `.env` 파일을 `.gitignore`에 추가 (이미 추가됨)
   - 환경 변수로만 관리

3. **방화벽 설정**
   - 필요한 포트만 공개
   - Neo4j Browser(7474)는 내부 네트워크에만 공개

4. **HTTPS 사용**
   - Nginx reverse proxy 추천
   - Let's Encrypt 무료 SSL 인증서

---

## 문의 및 지원

- GitHub Issues: https://github.com/VIK-GraphRAG/Finance_GraphRAG/issues
- Documentation: [SCHEMA.md](SCHEMA.md)

---

**배포 완료! 🚀**
