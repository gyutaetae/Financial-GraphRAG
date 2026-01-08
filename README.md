# Finance GraphRAG - Intelligent Document Analysis

## TEAM. VIK

테스터 : 경리 정민서  
기획, 개발 : 송대리  
백엔드 : 인턴 김대리  
프론트엔드 : 로사원  

<https://mobility.fpt.edu.vn/>

---

## 🚀 Quick Start

### 로컬 개발 (권장)

1. **환경 설정**
```bash
# .env 파일 생성
cp .env.example .env

# OpenAI API 키 설정
echo "OPENAI_API_KEY=your_key_here" >> .env
```

2. **서버 실행**
```bash
# FastAPI 백엔드
python src/app.py

# Streamlit 프론트엔드
streamlit run src/streamlit_app.py
```

### Docker Compose (프로덕션)

```bash
# 환경 변수 설정
export OPENAI_API_KEY=your_key_here
export NEO4J_PASSWORD=your_password_here

# 서비스 시작
docker-compose up -d

# 접속
# - Streamlit: http://localhost:8501
# - FastAPI: http://localhost:8000
# - Neo4j: http://localhost:7474
```

### Streamlit Cloud 배포

**Secrets 설정** (Settings → Secrets):
```toml
OPENAI_API_KEY = "your_key_here"
OPENAI_BASE_URL = "https://api.openai.com/v1"
```

**자동으로 직접 엔진 모드로 작동** (FastAPI 서버 불필요)

---

## 🌐 환경별 API URL 자동 설정

| 환경 | API_BASE_URL | 설명 |
|------|--------------|------|
| 로컬 개발 | `http://127.0.0.1:8000` | 기본값 |
| Docker Compose | `http://backend:8000` | 환경 변수로 자동 주입 |
| Streamlit Cloud | `None` | 직접 엔진 모드 (FastAPI 불필요) |

코드가 자동으로 환경을 감지하여 적절한 모드로 작동합니다.

---

## 📚 주요 기능

- **GraphRAG**: Neo4j 기반 지식 그래프 검색
- **Hybrid LLM**: OpenAI + Ollama 하이브리드 추론
- **Citation Validation**: 인용 검증 및 신뢰도 계산
- **Entity Resolution**: 다국어 개체명 통합
- **Dark Mode UI**: 최적화된 다크 테마
