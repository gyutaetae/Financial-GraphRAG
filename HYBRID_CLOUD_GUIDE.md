# 하이브리드 클라우드 전환 가이드

## 📋 완료된 리팩토링

### ✅ 1. 환경 변수 분리
- **파일**: `.env`, `.env.cloud.example`, `.env.docker`
- **관리 대상**: Neo4j URI/User/Password, Ollama URL, API Keys
- **도구**: `python-dotenv` 사용
- **위치**: `config.py`, `streamlit_app.py`, `health_check.py`

### ✅ 2. Neo4j Aura 대응
- **지원 프로토콜**:
  - `bolt://localhost:7687` (로컬)
  - `neo4j+s://xxxxx.databases.neo4j.io` (Aura 클라우드)
  - `neo4j+ssc://xxxxx.databases.neo4j.io` (Aura 자체 서명 인증서)

### ✅ 3. 배포용 파일
- `requirements.streamlit.txt` - Streamlit Cloud 전용
- `requirements.txt` - 전체 프로젝트 (Docker 포함)
- `.gitignore` - `.env`, `__pycache__` 제외

### ✅ 4. Ollama 접속 유연화
- **환경 변수**: `OLLAMA_BASE_URL`
- **지원 환경**:
  - `http://localhost:11434` (로컬)
  - `http://ollama:11434` (Docker)
  - `https://xxxx.ngrok.io` (Ngrok 터널)
  - 커스텀 클라우드 URL

### ✅ 5. Health Check 시스템
- **모듈**: `src/health_check.py`
- **기능**:
  - Neo4j 연결 확인 (로컬/Aura)
  - Ollama LLM 서버 확인
  - FastAPI 백엔드 확인
  - 친절한 에러 메시지
  - 환경 자동 감지

### ✅ 6. Streamlit 통합
- Health Check 모듈 통합
- 실시간 연결 상태 표시
- 환경별 자동 전환

## 🚀 배포 시나리오

### 시나리오 1: 완전 로컬 개발
```bash
# .env 설정
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=graphrag123
OLLAMA_BASE_URL=http://localhost:11434
API_BASE_URL=http://localhost:8000

# 실행
./restart.sh
```

### 시나리오 2: 하이브리드 (권장)
```bash
# .env 설정
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io  # Aura
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-aura-password
OLLAMA_BASE_URL=http://localhost:11434         # 로컬
API_BASE_URL=http://localhost:8000

# 실행
./restart.sh
```

### 시나리오 3: 완전 클라우드
```bash
# Streamlit Cloud Secrets
NEO4J_URI = "neo4j+s://xxxxx.databases.neo4j.io"
OLLAMA_BASE_URL = "https://xxxx.ngrok.io"
API_BASE_URL = "https://your-backend.com"

# 배포
# Streamlit Cloud 대시보드에서 자동 배포
```

### 시나리오 4: Docker 팀 협업
```bash
# .env.docker 설정
NEO4J_PASSWORD=graphrag123
OPENAI_API_KEY=sk-proj-xxxxx

# 실행
./start_team.sh
```

## 🔧 환경 전환 방법

### 로컬 → Aura 전환
```bash
# 1. Neo4j Aura 인스턴스 생성
# 2. .env 업데이트
sed -i '' 's|bolt://localhost:7687|neo4j+s://xxxxx.databases.neo4j.io|' .env

# 3. 비밀번호 변경
sed -i '' 's|NEO4J_PASSWORD=.*|NEO4J_PASSWORD=your-aura-password|' .env

# 4. 재시작
./restart.sh
```

### 로컬 Ollama → Ngrok 터널
```bash
# 1. Ngrok 터널 시작
ngrok http 11434

# 2. .env 업데이트
echo "OLLAMA_BASE_URL=https://xxxx.ngrok.io" >> .env

# 3. 재시작
./restart.sh
```

## 🏥 Health Check 사용법

### CLI에서 확인
```bash
cd /Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG
source .venv/bin/activate
python src/health_check.py
```

### Python 코드에서 사용
```python
from health_check import HealthChecker

checker = HealthChecker()

# 전체 서비스 체크
results = checker.check_all()
for service, (success, message) in results.items():
    print(f"{service}: {message}")

# 개별 서비스 체크
neo4j_ok, neo4j_msg = checker.check_neo4j()
ollama_ok, ollama_msg = checker.check_ollama()
backend_ok, backend_msg = checker.check_backend()

# 환경 정보 조회
env_info = checker.get_environment_info()
print(env_info)
```

### Streamlit에서 자동 체크
```python
# src/streamlit_app.py에서 자동으로 실행됨
# 우측 상단에 실시간 연결 상태 표시
```

## 📊 환경 감지 로직

Health Checker는 자동으로 환경을 감지합니다:

| 조건 | 감지 환경 |
|------|----------|
| `STREAMLIT_SHARING` 환경변수 존재 | Streamlit Cloud |
| `/.dockerenv` 파일 존재 | Docker |
| `neo4j+s://` URI 사용 | Hybrid (Aura) |
| 그 외 | Local Development |

## 🔒 보안 체크리스트

- [x] `.env` 파일 `.gitignore`에 추가됨
- [x] `__pycache__/` 제외됨
- [x] 환경 변수로 모든 민감 정보 관리
- [ ] Streamlit Secrets 설정 (배포 시)
- [ ] Neo4j Aura IP 화이트리스트 설정
- [ ] API 키 정기 변경

## 📁 주요 파일 구조

```
Finance_GraphRAG/
├── .env                        # 로컬 환경 변수 (gitignore)
├── .env.cloud.example          # 클라우드 설정 예제
├── .env.docker                 # Docker 설정 (gitignore)
├── .gitignore                  # 보안 파일 제외
├── requirements.txt            # 전체 의존성
├── requirements.streamlit.txt  # Streamlit Cloud 전용
├── src/
│   ├── config.py              # 환경 변수 로드 (dotenv)
│   ├── health_check.py        # 🆕 헬스 체크 모듈
│   ├── streamlit_app.py       # 🔄 Health Check 통합
│   └── ...
├── HYBRID_CLOUD_GUIDE.md      # 🆕 이 문서
├── STREAMLIT_DEPLOY.md        # 🆕 Streamlit Cloud 가이드
├── TEAM_SETUP.md              # 팀 협업 가이드
└── start_team.sh              # 팀 협업 시작 스크립트
```

## 🐛 문제 해결

### Neo4j 인증 실패
```bash
# 환경 변수 확인
grep NEO4J .env

# 연결 테스트
python src/health_check.py

# Aura 콘솔에서 비밀번호 재설정
```

### Ollama 연결 실패
```bash
# 로컬 Ollama 확인
curl http://localhost:11434/api/tags

# Ngrok 터널 확인
curl https://xxxx.ngrok.io/api/tags

# 환경 변수 확인
echo $OLLAMA_BASE_URL
```

### Streamlit 배포 실패
```bash
# requirements.streamlit.txt 확인
# Streamlit Cloud Logs 확인
# Secrets 설정 확인 (대소문자 정확히)
```

## 📚 관련 문서

- [팀 협업 설정](TEAM_SETUP.md)
- [Streamlit 배포](STREAMLIT_DEPLOY.md)
- [Docker 배포](DOCKER_DEPLOYMENT.md)
- [빠른 시작](QUICK_START.md)

## 🎯 다음 단계

1. **로컬 테스트**: `./restart.sh` 실행
2. **Health Check 확인**: `python src/health_check.py`
3. **Aura 전환**: Neo4j Aura 인스턴스 생성 후 `.env` 업데이트
4. **Streamlit 배포**: GitHub 푸시 후 Streamlit Cloud 연결
5. **팀 공유**: Streamlit Cloud URL 공유

---

**리팩토링 완료!** 🎉 이제 로컬/클라우드/하이브리드 환경을 자유롭게 전환할 수 있습니다.
