# 📂 Neo4j 데이터베이스 파일 위치

## 🎯 요약

Neo4j 그래프 데이터베이스는 **Docker 볼륨**에 저장되어 있습니다.

---

## 📍 데이터 위치

### 1. Docker 볼륨 (권장)

**컨테이너 내부 경로**:
```
/data/databases/neo4j/
```

**호스트 시스템 경로** (Mac의 경우):
```
/var/lib/docker/volumes/d2f75977172a9ca7cb9129334c36390fdfe5a096512e3cce2f2a76dc537313bb/_data
```

> ⚠️ **주의**: Mac에서는 Docker Desktop이 Linux VM 내에서 실행되므로, 이 경로는 실제로 VM 내부 경로입니다.

**현재 데이터베이스 크기**:
```
1.2 MB
```

---

## 🔍 데이터 확인 방법

### 방법 1: Docker 명령으로 확인 (가장 쉬움)

```bash
# Neo4j 컨테이너 ID 확인
docker ps --filter "name=neo4j"

# 데이터베이스 파일 목록
docker exec -it 2788e0d12e80 ls -lh /data/databases/neo4j/

# 데이터베이스 크기
docker exec -it 2788e0d12e80 du -sh /data/databases/neo4j/

# 데이터베이스 구조 확인
docker exec -it 2788e0d12e80 tree /data/databases/neo4j/
```

**출력 예시**:
```
/data/databases/neo4j/
├── neostore
├── neostore.counts.db
├── neostore.id
├── neostore.labeltokenstore.db
├── neostore.nodestore.db
├── neostore.propertystore.db
├── neostore.relationshipstore.db
└── ...
```

---

### 방법 2: Docker 볼륨으로 직접 접근

```bash
# 볼륨 이름 확인
docker volume ls

# 볼륨 상세 정보
docker volume inspect d2f75977172a9ca7cb9129334c36390fdfe5a096512e3cce2f2a76dc537313bb

# 볼륨 내용 확인 (임시 컨테이너 사용)
docker run --rm -v d2f75977172a9ca7cb9129334c36390fdfe5a096512e3cce2f2a76dc537313bb:/data busybox ls -lh /data/databases/neo4j
```

---

### 방법 3: Docker Desktop GUI (Mac)

1. **Docker Desktop 앱 실행**
2. **Volumes** 탭 클릭
3. `d2f7597717...` 볼륨 선택
4. **Data** 탭에서 파일 탐색

---

## 💾 데이터 백업 방법

### 1. Neo4j 내장 백업 (권장)

```bash
# 컨테이너에 접속
docker exec -it 2788e0d12e80 bash

# Neo4j 덤프 생성
neo4j-admin database dump neo4j --to=/data/backups/neo4j-backup-$(date +%Y%m%d).dump

# 호스트로 복사
exit
docker cp 2788e0d12e80:/data/backups/neo4j-backup-20260115.dump ~/Desktop/
```

---

### 2. Cypher 스크립트로 백업

```bash
# Python 스크립트 실행
cd /Users/gyuteoi/new/Finance_GraphRAG
python3 << 'EOF'
from neo4j import GraphDatabase
import os
from datetime import datetime

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 모든 노드와 관계 추출
with driver.session() as session:
    # 노드 개수
    result = session.run("MATCH (n) RETURN count(n) as count")
    node_count = result.single()["count"]
    
    # 관계 개수
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    rel_count = result.single()["count"]
    
    print(f"📊 Database Stats:")
    print(f"   Nodes: {node_count}")
    print(f"   Relationships: {rel_count}")
    
    # Cypher 스크립트 생성
    with open(f"neo4j_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.cypher", "w") as f:
        # 노드 내보내기
        result = session.run("MATCH (n) RETURN n LIMIT 1000")
        for record in result:
            node = record["n"]
            labels = ":".join(list(node.labels))
            props = dict(node)
            f.write(f"CREATE (:{labels} {props})\n")
        
        # 관계 내보내기
        result = session.run("MATCH (a)-[r]->(b) RETURN a, type(r) as rel, b, properties(r) as props LIMIT 1000")
        for record in result:
            f.write(f"// Relationship: {record['rel']}\n")

driver.close()
print("✅ Backup saved!")
EOF
```

---

### 3. Docker 볼륨 백업

```bash
# 볼륨 전체 백업 (tar 아카이브)
docker run --rm \
  -v d2f75977172a9ca7cb9129334c36390fdfe5a096512e3cce2f2a76dc537313bb:/data \
  -v $(pwd):/backup \
  busybox tar czf /backup/neo4j-volume-backup-$(date +%Y%m%d).tar.gz -C /data .

# 백업 파일 확인
ls -lh neo4j-volume-backup-*.tar.gz
```

---

## 🔄 데이터 복원 방법

### 1. Neo4j 덤프 복원

```bash
# 백업 파일을 컨테이너로 복사
docker cp ~/Desktop/neo4j-backup-20260115.dump 2788e0d12e80:/data/

# Neo4j 중지
docker exec 2788e0d12e80 neo4j stop

# 복원
docker exec 2788e0d12e80 neo4j-admin database load neo4j --from-path=/data/neo4j-backup-20260115.dump

# Neo4j 시작
docker exec 2788e0d12e80 neo4j start
```

---

### 2. Cypher 스크립트 복원

```bash
# Neo4j Browser에서 실행
# http://localhost:7474

# 또는 CLI로 실행
docker exec -it 2788e0d12e80 cypher-shell -u neo4j -p password < neo4j_backup_20260115.cypher
```

---

### 3. 볼륨 복원

```bash
# 새 볼륨 생성
docker volume create neo4j-data-restored

# 백업 복원
docker run --rm \
  -v neo4j-data-restored:/data \
  -v $(pwd):/backup \
  busybox tar xzf /backup/neo4j-volume-backup-20260115.tar.gz -C /data

# 새 Neo4j 컨테이너로 볼륨 마운트
docker run -d \
  --name neo4j-restored \
  -p 7475:7474 -p 7688:7687 \
  -v neo4j-data-restored:/data \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

---

## 📦 데이터 이동/공유

### 로컬 파일 시스템으로 복사

```bash
# 현재 프로젝트 폴더에 백업
cd /Users/gyuteoi/new/Finance_GraphRAG

# data 폴더 생성
mkdir -p neo4j_backup

# 데이터베이스 파일 복사
docker cp 2788e0d12e80:/data/databases/neo4j ./neo4j_backup/

# 확인
ls -lh neo4j_backup/neo4j/
```

**결과**:
```
/Users/gyuteoi/new/Finance_GraphRAG/neo4j_backup/neo4j/
├── neostore
├── neostore.counts.db
├── ...
```

---

## 🔧 유용한 명령어

### 데이터베이스 정보 확인

```bash
# 데이터베이스 목록
docker exec 2788e0d12e80 cypher-shell -u neo4j -p password "SHOW DATABASES"

# 데이터베이스 상태
docker exec 2788e0d12e80 cypher-shell -u neo4j -p password "CALL dbms.components()"

# 노드 통계
docker exec 2788e0d12e80 cypher-shell -u neo4j -p password "MATCH (n) RETURN labels(n) as label, count(*) as count"

# 관계 통계
docker exec 2788e0d12e80 cypher-shell -u neo4j -p password "MATCH ()-[r]->() RETURN type(r) as rel_type, count(*) as count"
```

---

## 🗂️ 파일 구조

```
Neo4j Data Volume
└── /data/
    ├── databases/
    │   ├── neo4j/           ⭐ 메인 데이터베이스
    │   │   ├── neostore                  # 그래프 스토어
    │   │   ├── neostore.nodestore.db     # 노드 데이터
    │   │   ├── neostore.relationshipstore.db  # 관계 데이터
    │   │   ├── neostore.propertystore.db # 속성 데이터
    │   │   └── ...
    │   └── system/          # 시스템 데이터베이스
    ├── transactions/        # 트랜잭션 로그
    └── logs/               # Neo4j 로그 파일
```

---

## 💡 팁

### 1. 실시간 크기 모니터링

```bash
# 5초마다 크기 확인
watch -n 5 'docker exec 2788e0d12e80 du -sh /data/databases/neo4j/'
```

---

### 2. 데이터베이스 압축

```bash
# Neo4j에서 사용하지 않는 데이터 정리
docker exec 2788e0d12e80 cypher-shell -u neo4j -p password "CALL apoc.periodic.iterate('MATCH (n) WHERE n.deprecated = true RETURN n', 'DETACH DELETE n', {batchSize:1000})"
```

---

### 3. 데이터 내보내기 (CSV)

```python
# Python 스크립트
from neo4j import GraphDatabase
import csv

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with driver.session() as session:
    # 노드 내보내기
    result = session.run("MATCH (n:Company) RETURN n.name as name, n.revenue as revenue")
    
    with open('companies.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Revenue'])
        for record in result:
            writer.writerow([record['name'], record['revenue']])

driver.close()
print("✅ Exported to companies.csv")
```

---

## 🚨 주의사항

### 1. 백업 주기
- **일일 백업**: 프로덕션 환경
- **주간 백업**: 개발 환경
- **중요 작업 전**: 수동 백업

### 2. 디스크 공간
```bash
# 사용 가능한 공간 확인
docker exec 2788e0d12e80 df -h /data
```

### 3. 데이터 무결성
```bash
# 일관성 체크
docker exec 2788e0d12e80 neo4j-admin check-consistency --database=neo4j
```

---

## 📞 문제 해결

### "No space left on device"
```bash
# 오래된 로그 삭제
docker exec 2788e0d12e80 rm -rf /data/logs/*.log

# 트랜잭션 로그 정리
docker exec 2788e0d12e80 neo4j-admin database prune-logs neo4j
```

### "Database is locked"
```bash
# Neo4j 재시작
docker restart 2788e0d12e80

# 또는 컨테이너 중지 후 시작
docker stop 2788e0d12e80
docker start 2788e0d12e80
```

---

## 📚 추가 자료

- **Neo4j 백업 가이드**: https://neo4j.com/docs/operations-manual/current/backup-restore/
- **Docker 볼륨 관리**: https://docs.docker.com/storage/volumes/

---

**마지막 업데이트**: 2026-01-15  
**컨테이너 ID**: 2788e0d12e80  
**볼륨 ID**: d2f75977172a9ca7cb9129334c36390fdfe5a096512e3cce2f2a76dc537313bb
