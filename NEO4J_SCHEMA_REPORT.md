# 📊 Neo4j 데이터베이스 스키마 리포트

**생성일**: 2026-01-15  
**데이터베이스**: Neo4j (bolt://localhost:7687)  
**총 노드 수**: 360개  
**총 관계 수**: 400+개

---

## 📋 목차

1. [노드 타입 (Labels)](#노드-타입-labels)
2. [관계 타입 (Relationships)](#관계-타입-relationships)
3. [주요 엔티티 상세](#주요-엔티티-상세)
4. [데이터 통계](#데이터-통계)
5. [스키마 다이어그램](#스키마-다이어그램)
6. [샘플 데이터](#샘플-데이터)

---

## 📌 노드 타입 (Labels)

### 전체 노드 레이블 목록

| 레이블 | 개수 | 설명 |
|--------|------|------|
| `FINANCIAL_METRIC` | 141 | 재무 지표 (매출, 이익 등) |
| `PRODUCT` | 76 | 제품/서비스 정보 |
| `COMPANY` | 72 | 회사 정보 (PDF 추출) |
| `LOCATION` | 22 | 위치/지역 정보 |
| `PERSON` | 20 | 인물 정보 (CEO, 임원 등) |
| `PRODUCT_FINANCIAL_METRIC` | 7 | 제품별 재무 지표 |
| `EVENT` | 6 | 이벤트/발표 |
| `Country` | 5 | 국가 (seed 데이터) |
| `Company` | 4 | 회사 (seed 데이터) |
| `Industry` | 3 | 산업 섹터 |
| `MacroIndicator` | 3 | 거시경제 지표 |
| `Person` | 1 | 인물 (seed 데이터) |
| `FinancialMetric` | 1 | 재무 지표 (seed 데이터) |

**총 노드 수**: 360개

---

## 🔗 관계 타입 (Relationships)

### 주요 관계 타입 (상위 20개)

| 관계 타입 | 개수 | 설명 | 예시 |
|-----------|------|------|------|
| `PRODUCES` | 62 | 제품 생산 | NVIDIA → Blackwell |
| `HAS_DEBT` | 30 | 부채 보유 | Company → FinancialMetric |
| `LOCATED_IN` | 29 | 위치 | TSMC → Taiwan |
| `COMPETES_WITH` | 28 | 경쟁 관계 | Nvidia → AMD |
| `OPERATES_IN` | 22 | 산업 분야 | Nvidia → Semiconductor |
| `INVESTS_IN` | 18 | 투자 | Company → Company |
| `HAS_CEO` | 17 | CEO 관계 | NVIDIA → Jensen Huang |
| `SUPPLIES` | 15 | 공급 관계 | TSMC → Nvidia |
| `PARTNERS_WITH` | 13 | 파트너십 | Nvidia → OpenAI |
| `REPORTED` | 11 | 보고/발표 | Company → FinancialMetric |
| `HAS_ASSET` | 10 | 자산 보유 | Company → Asset |
| `PURCHASES` | 9 | 구매 관계 | Company → Product |
| `HAS_VALUE` | 8 | 수치 값 | Metric → Value |
| `DEPENDS_ON` | 8 | 의존 관계 | Nvidia → TSMC |
| `EMPLOYS` | 7 | 고용 | Company → Person |
| `HAS_CUSTOMER` | 7 | 고객 관계 | Company → Customer |
| `HAS_PRODUCT` | 7 | 제품 보유 | Company → Product |
| `ANNOUNCED` | 6 | 발표 | Company → Event |
| `IMPACTS` | 6 | 영향 관계 | MacroIndicator → Industry |
| `PARTNERED_WITH` | 5 | 파트너 | Company → Company |

### 추가 관계 타입

- `THREATENS`: 위협 관계 (지정학적 리스크)
- `AFFECTS`: 영향 관계
- `HAS_METRIC`: 지표 보유
- `COLLABORATES_WITH`: 협업
- `EXTENDS_PLATFORM`: 플랫폼 확장
- `BOOST_AI_NETWORKING`: AI 네트워킹 부스트
- `HAS_FINANCIAL_MEASURE`: 재무 측정
- `BOOSTS_NETWORK`: 네트워크 부스트
- `RELATED_TO`: 관련 관계
- `CELEBRATED`: 기념/축하
- `REVEALED`: 공개
- `OWNS_ASSET`: 자산 소유
- `HAS_CFO`, `HAS_EXECUTIVE_VP`: 임원 관계

**총 관계 개수**: 400+ 개

---

## 🏢 주요 엔티티 상세

### 1. Company 노드 (seed 데이터)

**샘플**: Nvidia

```json
{
  "name": "Nvidia",
  "industry": "Semiconductor",
  "revenue": 60.9,
  "market_cap": 1200,
  "context": "Leading GPU manufacturer",
  "source": "PDF",
  "updated_at": "2026-01-15T09:34:48.254Z"
}
```

**주요 기업**:
- Nvidia
- TSMC
- AMD
- Intel

---

### 2. COMPANY 노드 (PDF 추출)

**샘플**: NVIDIA

```json
{
  "name": "NVIDIA",
  "ticker": "NVDA",
  "industry": "Technology",
  "revenue": "$51.2 billion",
  "operating_expenses": "$6.7 billion",
  "fiscal_year": "2026",
  "focus": "AI and computing",
  "products": [
    "Blackwell",
    "DGX Spark",
    "BlueField",
    "GeForce",
    "NVIDIA DRIVE AGX Hyperion",
    "NVIDIA IGX Thor",
    "NVIDIA Omniverse",
    "NVIDIA RTX PRO",
    "NVQLink",
    "Spectrum-X",
    "TensorRT",
    "NVLink Fusion"
  ],
  "source": "/tmp/tmpXXXX.txt",
  "extraction_method": "gpt-4o-mini-parallel",
  "chunk_index": 4,
  "page_number": 10,
  "char_count": 497,
  "lines": "44-56",
  "created_at": "2026-01-15T14:00:00.906702",
  "last_updated": "2026-01-15T14:00:00.906705"
}
```

**기타 COMPANY 노드**:
- Blackwell
- NVIDIA Blackwell
- OpenAI
- Google Cloud

---

### 3. MacroIndicator 노드

**샘플**:
- Taiwan Strait Tension (대만 해협 긴장)
- US-China Trade War (미중 무역전쟁)

```json
{
  "name": "Taiwan Strait Tension",
  "type": "geopolitical",
  "severity": 0.95
}
```

---

### 4. PRODUCT 노드

**주요 제품 (76개)**:
- Blackwell (NVIDIA GPU)
- DGX Spark
- BlueField
- GeForce
- NVIDIA DRIVE AGX Hyperion
- NVIDIA IGX Thor
- NVIDIA Omniverse
- NVIDIA RTX PRO
- NVLink
- Spectrum-X
- TensorRT

---

### 5. FINANCIAL_METRIC 노드 (141개)

**주요 재무 지표**:
- Revenue (매출)
- Operating Expenses (운영비용)
- Net Income (순이익)
- Market Cap (시가총액)
- Debt (부채)
- Assets (자산)

---

## 📊 데이터 통계

### 노드 분포

```
FINANCIAL_METRIC  ████████████████████████████ 141 (39%)
PRODUCT          ██████████████ 76 (21%)
COMPANY          ██████████████ 72 (20%)
LOCATION         ████ 22 (6%)
PERSON           ███ 20 (6%)
기타             ████ 29 (8%)
```

### 관계 분포

```
PRODUCES         ████████████████ 62 (15%)
HAS_DEBT         ████████ 30 (7%)
LOCATED_IN       ████████ 29 (7%)
COMPETES_WITH    ████████ 28 (7%)
OPERATES_IN      ██████ 22 (5%)
기타             ████████████████████████ 229+ (59%)
```

---

## 🗺️ 스키마 다이어그램

### 핵심 엔티티 관계도

```
┌──────────────┐
│   Company    │
│  (Nvidia)    │
└──────┬───────┘
       │
       ├─[DEPENDS_ON]────────┐
       │                     ▼
       │              ┌──────────────┐
       │              │   Company    │
       │              │   (TSMC)     │
       │              └──────┬───────┘
       │                     │
       │                     └─[LOCATED_IN]──┐
       │                                     ▼
       │                              ┌──────────────┐
       │                              │   Country    │
       │                              │  (Taiwan)    │
       │                              └──────▲───────┘
       │                                     │
       │                                     │
       ├─[COMPETES_WITH]──────┐             │
       │                      ▼             │
       │               ┌──────────────┐     │
       │               │   Company    │     │
       │               │   (AMD)      │     │
       │               └──────────────┘     │
       │                                    │
       ├─[OPERATES_IN]─────────────────┐   │
       │                               ▼   │
       │                        ┌──────────────┐
       │                        │   Industry   │
       │                        │(Semiconductor)│
       │                        └──────────────┘
       │
       ├─[PRODUCES]────────────┐
       │                       ▼
       │                ┌──────────────┐
       │                │   PRODUCT    │
       │                │ (Blackwell)  │
       │                └──────────────┘
       │
       └─[HAS_METRIC]──────────┐
                               ▼
                        ┌──────────────────┐
                        │ FinancialMetric  │
                        │   (Revenue)      │
                        └──────────────────┘

┌──────────────────┐
│ MacroIndicator   │
│(Taiwan Tension)  │
└────────┬─────────┘
         │
         └─[THREATENS]───────┐
                            ▼
                     ┌──────────────┐
                     │   Country    │
                     │  (Taiwan)    │
                     └──────────────┘
```

---

## 📝 샘플 데이터

### 샘플 1: Nvidia의 관계망

```cypher
MATCH (c:Company {name: 'Nvidia'})-[r]->(target)
RETURN c.name, type(r), labels(target)[0], target.name
LIMIT 10
```

**결과**:

| Company | Relationship | Target Type | Target Name |
|---------|--------------|-------------|-------------|
| Nvidia | OPERATES_IN | Industry | TSMC |
| Nvidia | DEPENDS_ON | Company | TSMC |
| Nvidia | HAS_METRIC | FinancialMetric | Revenue |
| Nvidia | COMPETES_WITH | Company | Intel |
| Nvidia | COMPETES_WITH | Company | AMD |

---

### 샘플 2: NVIDIA (PDF 추출) 상세 정보

```cypher
MATCH (c:COMPANY {name: 'NVIDIA'})
RETURN properties(c)
```

**결과**:
- **Ticker**: NVDA
- **Industry**: Technology
- **Revenue**: $51.2 billion
- **Operating Expenses**: $6.7 billion
- **Fiscal Year**: 2026
- **Products**: 12개 (Blackwell, DGX Spark, BlueField 등)
- **Source**: PDF (/tmp/tmp_s3lyhee.txt)
- **Extraction Method**: gpt-4o-mini-parallel

---

### 샘플 3: 지정학적 리스크 체인

```cypher
MATCH path = (m:MacroIndicator)-[:THREATENS]->(c:Country)
              <-[:LOCATED_IN]-(comp:Company)
RETURN path
```

**결과**:
```
Taiwan Strait Tension → THREATENS → Taiwan
                                      ↑
                                      └── LOCATED_IN ← TSMC
```

---

## 🔍 유용한 쿼리

### 1. 전체 노드 타입 확인

```cypher
MATCH (n)
RETURN labels(n) as label, count(*) as count
ORDER BY count DESC
```

---

### 2. 특정 기업의 모든 관계

```cypher
MATCH (c:Company {name: 'Nvidia'})-[r]-(related)
RETURN c.name, type(r), labels(related), related.name
```

---

### 3. 경쟁사 네트워크

```cypher
MATCH (c1:Company)-[:COMPETES_WITH]-(c2:Company)
RETURN c1.name, c2.name
```

---

### 4. 공급망 관계

```cypher
MATCH path = (supplier)-[:SUPPLIES]->(company)-[:PRODUCES]->(product)
RETURN path
```

---

### 5. 재무 지표 순위

```cypher
MATCH (c:Company)-[:HAS_METRIC]->(m:FinancialMetric)
WHERE m.name = 'Revenue'
RETURN c.name, m.value
ORDER BY m.value DESC
```

---

## 📈 데이터 품질 분석

### 데이터 소스

1. **Seed Data** (수동 입력):
   - Company (4개): Nvidia, TSMC, AMD, Intel
   - Country (5개): Taiwan, USA 등
   - MacroIndicator (3개): 지정학적 리스크

2. **PDF 추출** (자동):
   - COMPANY (72개): NVIDIA, Blackwell, OpenAI 등
   - PRODUCT (76개): Blackwell, DGX Spark 등
   - FINANCIAL_METRIC (141개): Revenue, Expenses 등
   - 추출 방법: gpt-4o-mini-parallel

3. **혼합 데이터**:
   - PERSON (20개): CEO, 임원
   - LOCATION (22개): 지역 정보
   - EVENT (6개): 발표, 이벤트

---

## ⚠️ 데이터 중복 이슈

### 발견된 중복

**문제**: `Company`와 `COMPANY` 레이블이 분리되어 있음

**예시**:
- `(:Company {name: 'Nvidia'})` (seed 데이터)
- `(:COMPANY {name: 'NVIDIA'})` (PDF 추출)

**영향**:
- Nvidia → DEPENDS_ON → TSMC 관계가 중복 생성
- 데이터 일관성 저하

**해결 방안**:

```cypher
// 1. Company → COMPANY로 통합
MATCH (old:Company)
MERGE (new:COMPANY {name: old.name})
SET new += properties(old)
WITH old, new
MATCH (old)-[r]->(target)
MERGE (new)-[r2:TYPE(r)]->(target)
SET r2 = properties(r)
DETACH DELETE old

// 2. 또는 별칭 해석 강화 (integrator.py)
EntityResolver.add_alias('Nvidia', ['NVIDIA', 'nvidia', 'Nvidia'])
```

---

## 🔧 스키마 개선 제안

### 1. 인덱스 추가

```cypher
// 성능 향상을 위한 인덱스
CREATE INDEX company_name IF NOT EXISTS FOR (c:COMPANY) ON (c.name);
CREATE INDEX company_ticker IF NOT EXISTS FOR (c:COMPANY) ON (c.ticker);
CREATE INDEX product_name IF NOT EXISTS FOR (p:PRODUCT) ON (p.name);
CREATE INDEX metric_name IF NOT EXISTS FOR (m:FINANCIAL_METRIC) ON (m.name);
```

---

### 2. 제약 조건 추가

```cypher
// 중복 방지
CREATE CONSTRAINT company_unique IF NOT EXISTS
FOR (c:COMPANY) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT product_unique IF NOT EXISTS
FOR (p:PRODUCT) REQUIRE p.name IS UNIQUE;
```

---

### 3. 레이블 통일

**제안**: 모든 레이블을 PascalCase로 통일

```
Before:              After:
COMPANY         →    Company
FINANCIAL_METRIC →   FinancialMetric
PRODUCT         →    Product
PERSON          →    Person
```

---

## 📊 데이터 백업 권장사항

### 정기 백업

```bash
# 주간 백업
docker exec 2788e0d12e80 neo4j-admin database dump neo4j \
  --to=/data/backups/weekly-$(date +%Y%m%d).dump

# 호스트로 복사
docker cp 2788e0d12e80:/data/backups/weekly-*.dump ./backups/
```

---

## 🔗 관련 문서

- [Neo4j Data Location Guide](NEO4J_DATA_LOCATION.md)
- [Integration Complete Guide](INTEGRATION_COMPLETE.md)
- [Multi-Hop Reasoning Guide](MULTIHOP_REASONING_GUIDE.md)

---

**생성일**: 2026-01-15  
**데이터베이스 버전**: Neo4j 5.x  
**데이터 크기**: 1.2 MB  
**마지막 업데이트**: 2026-01-15T09:34:48Z
