# 🚀 빠른 시작 가이드

## 📋 단계별 실행 방법

### 1️⃣ Neo4j 시작

```bash
cd /Users/gyuteoi/new/Finance_GraphRAG

# Neo4j Docker 컨테이너 시작 (이미 실행 중이면 스킵)
docker ps | grep neo4j
```

**결과**: Neo4j가 실행 중이어야 합니다 (포트 7474, 7687)

---

### 2️⃣ 초기 데이터 생성 (처음 1회만)

```bash
# Finance_GraphRAG 폴더로 이동
cd /Users/gyuteoi/new/Finance_GraphRAG

# Seed 데이터 생성
python3 seed_financial_data.py
```

**출력 예시**:
```
✅ Connected to Neo4j
✅ 1/24
✅ 2/24
...
✅ 24/24
✅ Seed data complete!
```

**생성되는 데이터**:
- 기업: Nvidia, TSMC, AMD, Intel, Samsung Electronics
- 국가: United States, Taiwan, South Korea, China, Japan
- 산업: Semiconductor, Technology, Manufacturing
- 거시경제 지표: Taiwan Strait Tension, US-China Trade War, AI Boom

---

### 3️⃣ 웹 인터페이스 시작

```bash
# 모든 서비스 시작 (FastAPI + Streamlit)
./start.sh
```

**또는 수동으로**:
```bash
# 백엔드 시작
python3 src/app.py &

# 프론트엔드 시작
streamlit run src/streamlit_app.py --server.port 8501
```

**접속**: http://localhost:8501

---

### 4️⃣ 그래프 확인

1. **브라우저 열기**: http://localhost:8501
2. **탭 클릭**: "🕸️ Graph Visualizer" 탭
3. **데이터 확인**: 그래프가 자동으로 표시됩니다!

---

## 🎨 그래프 비주얼라이저 사용법

### 📍 모드 선택

#### 1. **All Nodes** (기본)
- 전체 그래프 보기
- 노드 수 조절: 슬라이더로 10~500개

```
💡 추천: 처음에는 50개로 시작하세요
```

---

#### 2. **Company Focus** (기업 중심)
- 특정 기업의 관계망 탐색
- 선택 가능: Nvidia, TSMC, AMD, Intel, Samsung Electronics

**예시 - Nvidia 선택 시**:
```
Nvidia (중심)
  ├─ DEPENDS_ON → TSMC
  ├─ OPERATES_IN → Semiconductor
  ├─ COMPETES_WITH → AMD, Intel
  └─ LOCATED_IN → United States
```

---

#### 3. **Risk Analysis** (리스크 분석)
- 거시경제 지표의 영향 관계
- 지정학적 리스크 체인 시각화

**표시되는 관계**:
```
Taiwan Strait Tension
  └─ IMPACTS → Taiwan
      └─ LOCATED_IN ← TSMC
          └─ DEPENDS_ON ← Nvidia
```

---

#### 4. **Custom Query** (커스텀 쿼리)
- Cypher 쿼리 직접 입력
- 고급 사용자용

**예시 쿼리**:
```cypher
MATCH (c:Company)-[:COMPETES_WITH]-(competitor)
RETURN c, competitor
LIMIT 20
```

---

## 🔧 인터랙티브 기능

### 노드 조작
- **드래그**: 노드 위치 이동
- **클릭**: 노드 선택 및 연결 확인
- **호버**: 노드 정보 툴팁 표시

### 그래프 탐색
- **휠 스크롤**: 줌 인/아웃
- **드래그 (빈 공간)**: 그래프 이동
- **네비게이션 버튼**: 우측 하단 컨트롤

### 물리 시뮬레이션
- 자동으로 노드 배치 최적화
- 안정화 완료 후 자동 중지

---

## 📊 통계 확인

그래프 상단에 실시간 통계가 표시됩니다:

```
📍 Nodes: 361        # 현재 표시된 노드 수
🔗 Edges: 400+       # 현재 표시된 관계 수
📊 Density: 1.11     # 그래프 밀도 (edges/nodes)
```

---

## 🎨 색상 구분

| 색상 | 노드 타입 | 예시 |
|------|-----------|------|
| 🔴 | Company | Nvidia, TSMC, AMD |
| 🔵 | Country | Taiwan, United States |
| 🟢 | Industry | Semiconductor, Technology |
| 🟠 | MacroIndicator | Taiwan Tension, Trade War |
| 🟣 | FinancialMetric | Revenue, Market Cap |

---

## ❓ 문제 해결

### 1. "No graph data found" 메시지

**원인**: 데이터가 생성되지 않음

**해결**:
```bash
cd /Users/gyuteoi/new/Finance_GraphRAG
python3 seed_financial_data.py
```

---

### 2. Neo4j 연결 오류

**확인**:
```bash
# Neo4j 실행 확인
docker ps | grep neo4j

# 없으면 시작
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

---

### 3. 그래프가 느리게 로드됨

**해결**: 노드 수 줄이기
- 슬라이더를 50 이하로 설정
- Company Focus 모드 사용

---

### 4. 페이지가 로드되지 않음

**확인**:
```bash
# Streamlit 실행 확인
lsof -i :8501

# 없으면 재시작
cd /Users/gyuteoi/new/Finance_GraphRAG
./start.sh
```

---

## 📚 다음 단계

### 1. PDF 업로드
- "Data Ingestion" 탭으로 이동
- PDF 파일 업로드
- 자동 인덱싱 및 그래프 업데이트

### 2. 질문하기
- "Query Interface" 탭으로 이동
- 자연어 질문 입력
- 예: "Nvidia의 공급망 리스크는?"

### 3. 고급 쿼리
- "Graph Visualizer" 탭
- Custom Query 모드 선택
- Cypher 쿼리로 복잡한 분석

---

## 🔗 관련 문서

| 문서 | 설명 |
|------|------|
| [README.md](README.md) | 프로젝트 개요 |
| [NEO4J_SCHEMA_REPORT.md](NEO4J_SCHEMA_REPORT.md) | 데이터베이스 스키마 |
| [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) | 통합 가이드 |
| [MULTIHOP_REASONING_GUIDE.md](MULTIHOP_REASONING_GUIDE.md) | 추론 시스템 |

---

## 💡 유용한 명령어

### 데이터베이스 확인
```bash
# 노드 개수
docker exec 2788e0d12e80 cypher-shell -u neo4j -p password \
  "MATCH (n) RETURN count(n)"

# 관계 개수
docker exec 2788e0d12e80 cypher-shell -u neo4j -p password \
  "MATCH ()-[r]->() RETURN count(r)"

# 기업 목록
docker exec 2788e0d12e80 cypher-shell -u neo4j -p password \
  "MATCH (c:Company) RETURN c.name"
```

---

### 데이터 백업
```bash
# 백업
docker exec 2788e0d12e80 neo4j-admin database dump neo4j \
  --to=/data/backups/backup-$(date +%Y%m%d).dump

# 호스트로 복사
docker cp 2788e0d12e80:/data/backups/ ./backups/
```

---

### 시스템 재시작
```bash
# 모든 서비스 재시작
cd /Users/gyuteoi/new/Finance_GraphRAG
./restart.sh
```

---

## 🎉 완료!

이제 다음을 할 수 있습니다:
- ✅ 그래프 데이터 시각화
- ✅ 기업 관계망 탐색
- ✅ 리스크 체인 분석
- ✅ PDF 업로드 및 자동 인덱싱
- ✅ 자연어 질문 & 답변

**접속**: http://localhost:8501  
**탭**: 🕸️ Graph Visualizer

---

**마지막 업데이트**: 2026-01-15  
**버전**: 3.0
