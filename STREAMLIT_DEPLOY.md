# Streamlit Cloud 배포 가이드

## 사전 준비

### 1. Neo4j Aura 계정 생성
1. https://neo4j.com/cloud/aura/ 접속
2. Free Tier 선택 (65k nodes, 175k relationships)
3. 인스턴스 생성 후 다음 정보 저장:
   - URI: `neo4j+s://xxxxx.databases.neo4j.io`
   - Username: `neo4j`
   - Password: 생성된 비밀번호

### 2. Ollama 접근 설정 (선택사항)
로컬 Ollama를 클라우드에서 사용하려면 Ngrok 터널 필요:

```bash
# Ngrok 설치
brew install ngrok

# Ollama 터널링
ngrok http 11434

# 생성된 URL 저장: https://xxxx.ngrok.io
```

### 3. GitHub 저장소 준비
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/Finance-GraphRAG.git
git push -u origin main
```

## Streamlit Cloud 배포

### 1. Streamlit Cloud 설정
1. https://streamlit.io/cloud 접속
2. GitHub 연동
3. "New app" 클릭
4. 저장소 선택: `yourusername/Finance-GraphRAG`
5. Main file: `src/streamlit_app.py`
6. Python version: `3.11`

### 2. Secrets 설정
Streamlit Cloud 대시보드에서 "Settings" → "Secrets" 추가:

```toml
# .streamlit/secrets.toml 형식
OPENAI_API_KEY = "sk-proj-your-key-here"
OPENAI_BASE_URL = "https://api.openai.com/v1"

NEO4J_URI = "neo4j+s://xxxxx.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your-aura-password"

OLLAMA_BASE_URL = "https://xxxx.ngrok.io"
API_BASE_URL = "http://localhost:8000"

TAVILY_API_KEY = "tvly-your-key-here"
RUN_MODE = "API"
```

### 3. 배포 확인
- Streamlit Cloud가 자동으로 빌드 시작
- 로그에서 `requirements.streamlit.txt` 설치 확인
- 배포 완료 후 URL 접근: `https://yourusername-finance-graphrag.streamlit.app`

## 하이브리드 아키텍처

### 시나리오 1: 완전 클라우드
```
Streamlit Cloud (Frontend)
    ↓
Neo4j Aura (Database)
    ↓
OpenAI API (LLM)
```

**장점**: 완전 관리형, 확장 용이  
**단점**: API 비용 발생

### 시나리오 2: 하이브리드 (권장)
```
Streamlit Cloud (Frontend)
    ↓
Neo4j Aura (Database)
    ↓
로컬 Ollama via Ngrok (LLM)
```

**장점**: LLM 비용 절감, 데이터 클라우드 백업  
**단점**: Ngrok 터널 유지 필요

### 시나리오 3: 완전 로컬
```
로컬 Streamlit
    ↓
로컬 Neo4j
    ↓
로컬 Ollama
```

**장점**: 완전 무료, 프라이버시  
**단점**: 팀 협업 어려움

## 환경별 설정

### 개발 환경 (.env)
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=graphrag123
OLLAMA_BASE_URL=http://localhost:11434
API_BASE_URL=http://localhost:8000
```

### 프로덕션 환경 (Streamlit Secrets)
```toml
NEO4J_URI = "neo4j+s://xxxxx.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your-aura-password"
OLLAMA_BASE_URL = "https://xxxx.ngrok.io"
API_BASE_URL = "https://your-backend.com"
```

## 문제 해결

### Neo4j Aura 연결 실패
```bash
# 1. URI 형식 확인
neo4j+s://xxxxx.databases.neo4j.io  # ✅ 올바름
bolt://xxxxx.databases.neo4j.io     # ❌ 틀림

# 2. 비밀번호 재설정
# Aura 콘솔에서 비밀번호 재설정

# 3. IP 화이트리스트 확인
# Aura 콘솔 → Security → "0.0.0.0/0" 허용
```

### Ollama Ngrok 터널 문제
```bash
# 터널 상태 확인
curl https://xxxx.ngrok.io/api/tags

# 터널 재시작
ngrok http 11434

# 영구 도메인 (Ngrok Pro 필요)
ngrok http 11434 --domain=your-domain.ngrok.io
```

### 배포 실패
```bash
# 로그 확인
# Streamlit Cloud 대시보드 → Logs

# 일반적인 원인:
# 1. requirements.txt 누락
# 2. Secrets 미설정
# 3. Python 버전 불일치
```

## 성능 최적화

### 1. 캐싱 활용
```python
@st.cache_data(ttl=3600)
def cached_query(question):
    return api_call(question)
```

### 2. 연결 풀링
```python
@st.cache_resource
def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(user, password))
```

### 3. 비동기 처리
```python
import asyncio
result = asyncio.run(async_query(question))
```

## 비용 예측

### Neo4j Aura Free Tier
- 65,000 nodes
- 175,000 relationships
- 50MB storage
- **비용**: 무료

### OpenAI API
- GPT-4o-mini: $0.15/1M input tokens
- 평균 query: ~1000 tokens
- **예상 비용**: 100 queries ≈ $0.015

### Streamlit Cloud
- 1 public app: 무료
- 리소스: 1GB RAM, shared CPU
- **비용**: 무료

**총 비용**: ~$0-5/월 (API 사용량에 따라)

## 보안 체크리스트

- [ ] `.env` 파일을 `.gitignore`에 추가
- [ ] Streamlit Secrets에 API 키 저장
- [ ] Neo4j Aura IP 화이트리스트 설정
- [ ] HTTPS 강제 (Streamlit Cloud 기본 제공)
- [ ] 비밀번호 정기 변경
- [ ] 로그에 민감정보 노출 방지

## 참고 자료

- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Neo4j Aura Docs](https://neo4j.com/docs/aura/)
- [Ngrok Docs](https://ngrok.com/docs)
