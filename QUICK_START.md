# Finance GraphRAG 빠른 시작 가이드 🚀

## 📦 Docker로 빠르게 시작하기 (권장)

### 1단계: 환경 설정

```bash
# 1. .env 파일 생성
cp env.docker.example .env

# 2. .env 파일 편집
nano .env
```

**필수 입력 항목:**
```bash
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx  # OpenAI API 키
NEO4J_PASSWORD=YourPassword123!        # Neo4j 비밀번호
```

### 2단계: 자동 배포

```bash
# 배포 스크립트 실행
./deploy.sh
```

### 3단계: 접속

- **Streamlit UI**: http://localhost:8501
- **FastAPI API**: http://localhost:8000/docs

---

## 🏗️ 새로운 기능: 도메인 스키마

Event-Actor-Asset-Factor-Region 도메인 스키마가 추가되었습니다!

### 도메인 스키마 초기화

```bash
curl -X POST http://localhost:8000/domain/schema/init
```

또는 Streamlit UI의 "🏗️ Domain Analysis" 탭에서 버튼 클릭

### 도메인 분석 API

```bash
# Event 인과관계 조회
curl http://localhost:8000/domain/event/Fed%20금리%20인상

# Actor 영향력 조회
curl http://localhost:8000/domain/actor/Federal%20Reserve

# Region 이벤트 조회
curl http://localhost:8000/domain/region/중국

# Asset 요인 분석
curl http://localhost:8000/domain/asset/금
```

---

## 📝 수동 설치 (로컬 개발)

```bash
# 1. 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp env.example .env
nano .env

# 4. 서버 실행
python src/app.py
```

---

## 🔧 주요 설정

### LLM 모델

**API 모드**: OpenAI GPT-4o-mini
**LOCAL 모드**: Qwen2.5-Coder-3B (Ollama)

```bash
# .env에서 모드 선택
RUN_MODE=API   # OpenAI 사용 (권장)
RUN_MODE=LOCAL # Ollama(Qwen2.5-Coder) 사용
```

### MCP 서버 (Multi-Context Protocol)

**Yahoo Finance**: 실시간 주가 및 재무 데이터
**Tavily Search**: 최신 뉴스 및 웹 검색

```bash
# .env에서 활성화
TAVILY_API_KEY=tvly-xxxxxxxxxxxxx
MCP_LAZY_LOAD=true
```

### 도메인 스키마

```bash
# .env에서 활성화
ENABLE_DOMAIN_SCHEMA=true
DOMAIN_CLASSIFICATION_MODEL=gpt-4o-mini
```

---

## 📊 아키텍처

```
┌─────────────────┐
│  Streamlit UI   │ :8501
└────────┬────────┘
         │
┌────────▼────────┐
│  FastAPI        │ :8000
│  + GraphRAG     │
│  + MCP Servers  │
└────────┬────────┘
         │
┌────────▼────────┐
│  Neo4j          │ :7474, :7687
│  Graph Database │
└─────────────────┘
```

---

## 🌐 팀원에게 공유하기

### 로컬 네트워크

```bash
# 본인 IP 확인
ifconfig | grep "inet " | grep -v 127.0.0.1  # Mac/Linux
ipconfig  # Windows

# 팀원 접속 URL
http://YOUR_IP:8501  # Streamlit
http://YOUR_IP:8000  # API
```

### 클라우드 서버

자세한 내용은 [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) 참고

---

## 🛠️ 문제 해결

### 포트 충돌
```bash
# 사용 중인 포트 확인
lsof -i :8000
lsof -i :8501

# 프로세스 종료
kill -9 <PID>
```

### 컨테이너 재시작
```bash
docker-compose restart backend
docker-compose logs -f backend
```

### 전체 초기화
```bash
docker-compose down -v  # 데이터 포함 전체 삭제
./deploy.sh             # 재배포
```

---

## 📚 추가 문서

- [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) - 상세 배포 가이드
- [SCHEMA.md](SCHEMA.md) - 도메인 스키마 설명
- [env.example](env.example) - 환경 변수 설명

---

## 🎯 다음 단계

1. **데이터 인덱싱**: Streamlit UI의 "Data Ingestion" 탭에서 PDF 업로드
2. **질문하기**: "Query Interface" 탭에서 질문 입력
3. **도메인 분석**: "Domain Analysis" 탭에서 Event/Actor/Asset 관계 탐색
4. **그래프 탐색**: Neo4j Browser(http://localhost:7474)에서 그래프 시각화

---

**문의**: GitHub Issues 또는 팀 채널로 연락 주세요!
