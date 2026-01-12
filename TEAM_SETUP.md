# 팀 협업 설정 가이드

## 필수 사항

### 1. OrbStack 또는 Docker Desktop 설치
- **Mac**: [OrbStack](https://orbstack.dev/) 권장 (8GB RAM 최적화)
- **Windows/Linux**: Docker Desktop

### 2. 프로젝트 클론
```bash
git clone https://github.com/your-repo/Finance_GraphRAG.git
cd Finance_GraphRAG
```

## 빠른 시작

### 1. 환경 변수 설정
`.env.docker` 파일을 생성하고 API 키 설정:

```bash
# .env.docker
OPENAI_API_KEY=sk-proj-xxxxx
NEO4J_PASSWORD=graphrag123
TAVILY_API_KEY=tvly-xxxxx  # 선택사항
RUN_MODE=API
```

### 2. 서비스 시작
```bash
./start_team.sh
```

### 3. 접속
- **Streamlit UI**: http://localhost:8501
- **FastAPI 문서**: http://localhost:8000/docs
- **Neo4j 브라우저**: http://localhost:7474

## 로컬 네트워크에서 팀원 접속

### 호스트 (본인) 설정
1. 본인의 IP 주소 확인:
```bash
# Mac
ipconfig getifaddr en0

# Windows
ipconfig

# Linux
hostname -I
```

2. 팀원들에게 공유:
```
http://192.168.x.x:8501  # 본인의 IP 주소
```

### 팀원 접속
- 같은 Wi-Fi 네트워크에 연결
- 공유받은 주소로 접속

## 주요 명령어

```bash
# 전체 시작
./start_team.sh

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f frontend
docker-compose logs -f backend

# 재시작
docker-compose restart

# 중지
docker-compose down

# 완전 초기화 (데이터 삭제)
docker-compose down -v
```

## 문제 해결

### 포트 충돌
다른 서비스가 이미 포트를 사용 중인 경우:
```bash
# 포트 사용 확인
lsof -i :8501  # Streamlit
lsof -i :8000  # FastAPI
lsof -i :7474  # Neo4j

# 프로세스 종료
kill -9 <PID>
```

### 메모리 부족 (8GB RAM)
```bash
# 불필요한 컨테이너 정리
docker system prune -a

# Ollama 대신 OpenAI API만 사용
RUN_MODE=API
```

### Neo4j 연결 실패
```bash
# Neo4j 상태 확인
docker-compose ps neo4j

# Neo4j 재시작
docker-compose restart neo4j
```

## 개발 모드

코드 수정 시 자동 리로드:
```bash
# backend는 자동 리로드 활성화됨 (--reload)
# frontend도 자동 리로드됨

# 수동 재시작
docker-compose restart backend
docker-compose restart frontend
```

## 프로덕션 배포

AWS/GCP/Azure에 배포 시:
1. `.env.docker`에 프로덕션 API 키 설정
2. `docker-compose.yml`에서 포트 보안 설정
3. HTTPS 인증서 설정 (nginx 등)
4. 방화벽 규칙 설정
