"""
Neo4j 기반 정밀 컨텍스트/근거 추출기

규칙(cursorrules.mdc):
- Precision over Recall: 2-hop+ 관계 탐색 + 속성 필터링
- Parameterized Cypher + strict LIMIT
- Neo4j 응답은 Pydantic 모델로 파싱/검증
"""

from __future__ import annotations

from dataclasses import dataclass
import time
import re
from typing import Dict, List, Optional, Tuple

from engine.executor import QueryExecutor
from models.neo4j_models import Neo4jQueryResult
from entity_resolver import EntityResolver


# 도메인 특화 쿼리 함수들
def query_event_impact_chain(executor: QueryExecutor, event_name: str) -> List[Dict]:
    """
    Event → Factor → Asset 인과관계 체인 조회
    
    Args:
        executor: QueryExecutor 인스턴스
        event_name: Event 이름
    
    Returns:
        인과관계 체인 리스트
    """
    query = """
    MATCH (e:Event {name: $event_name})-[:TRIGGERS]->(f:Factor)
    MATCH (f)-[i:IMPACTS]->(a:Asset)
    RETURN e.name as event_name, e.date as event_date, e.impact_level as impact_level,
           f.name as factor_name, f.type as factor_type,
           i.direction as impact_direction, i.magnitude as impact_magnitude, i.confidence as impact_confidence,
           a.name as asset_name, a.type as asset_type
    ORDER BY i.magnitude DESC
    LIMIT 10
    """
    
    try:
        result = executor.execute_query(query, {"event_name": event_name})
        
        impact_chain = []
        for record in result.records:
            impact_chain.append({
                "event": {
                    "name": record.get("event_name", ""),
                    "date": record.get("event_date", ""),
                    "impact_level": record.get("impact_level", "")
                },
                "factor": {
                    "name": record.get("factor_name", ""),
                    "type": record.get("factor_type", "")
                },
                "impact": {
                    "direction": record.get("impact_direction", ""),
                    "magnitude": record.get("impact_magnitude", 0.0),
                    "confidence": record.get("impact_confidence", 0.0)
                },
                "asset": {
                    "name": record.get("asset_name", ""),
                    "type": record.get("asset_type", "")
                }
            })
        
        return impact_chain
    
    except Exception as e:
        print(f"⚠️  Event impact chain 조회 중 에러: {e}")
        return []


def query_actor_influence(executor: QueryExecutor, actor_name: str) -> List[Dict]:
    """
    Actor가 관여한 Event와 그 영향 조회
    
    Args:
        executor: QueryExecutor 인스턴스
        actor_name: Actor 이름
    
    Returns:
        Actor 영향력 리스트
    """
    query = """
    MATCH (actor:Actor {name: $actor_name})-[inv:INVOLVED_IN]->(e:Event)
    MATCH (e)-[:TRIGGERS]->(f:Factor)-[i:IMPACTS]->(a:Asset)
    RETURN actor.name as actor_name, actor.type as actor_type,
           inv.role as actor_role, inv.influence_level as influence_level,
           e.name as event_name, e.date as event_date,
           f.name as factor_name, f.type as factor_type,
           i.direction as impact_direction, i.magnitude as impact_magnitude,
           a.name as asset_name, a.type as asset_type
    ORDER BY e.date DESC
    LIMIT 20
    """
    
    try:
        result = executor.execute_query(query, {"actor_name": actor_name})
        
        influence_data = []
        for record in result.records:
            influence_data.append({
                "actor": {
                    "name": record.get("actor_name", ""),
                    "type": record.get("actor_type", ""),
                    "role": record.get("actor_role", ""),
                    "influence_level": record.get("influence_level", "")
                },
                "event": {
                    "name": record.get("event_name", ""),
                    "date": record.get("event_date", "")
                },
                "factor": {
                    "name": record.get("factor_name", ""),
                    "type": record.get("factor_type", "")
                },
                "impact": {
                    "direction": record.get("impact_direction", ""),
                    "magnitude": record.get("impact_magnitude", 0.0)
                },
                "asset": {
                    "name": record.get("asset_name", ""),
                    "type": record.get("asset_type", "")
                }
            })
        
        return influence_data
    
    except Exception as e:
        print(f"⚠️  Actor influence 조회 중 에러: {e}")
        return []


def query_regional_events(executor: QueryExecutor, region_name: str) -> List[Dict]:
    """
    특정 지역의 Event와 영향받은 Asset 조회
    
    Args:
        executor: QueryExecutor 인스턴스
        region_name: Region 이름
    
    Returns:
        지역별 Event 리스트
    """
    query = """
    MATCH (e:Event)-[loc:LOCATED_IN]->(r:Region {name: $region_name})
    MATCH (e)-[:TRIGGERS]->(f:Factor)-[i:IMPACTS]->(a:Asset)
    RETURN e.name as event_name, e.date as event_date, e.impact_level as impact_level,
           loc.impact_scope as impact_scope,
           r.name as region_name, r.type as region_type,
           f.name as factor_name, f.type as factor_type,
           i.direction as impact_direction, i.magnitude as impact_magnitude,
           a.name as asset_name, a.type as asset_type
    ORDER BY e.date DESC
    LIMIT 15
    """
    
    try:
        result = executor.execute_query(query, {"region_name": region_name})
        
        regional_events = []
        for record in result.records:
            regional_events.append({
                "event": {
                    "name": record.get("event_name", ""),
                    "date": record.get("event_date", ""),
                    "impact_level": record.get("impact_level", "")
                },
                "region": {
                    "name": record.get("region_name", ""),
                    "type": record.get("region_type", ""),
                    "impact_scope": record.get("impact_scope", "")
                },
                "factor": {
                    "name": record.get("factor_name", ""),
                    "type": record.get("factor_type", "")
                },
                "impact": {
                    "direction": record.get("impact_direction", ""),
                    "magnitude": record.get("impact_magnitude", 0.0)
                },
                "asset": {
                    "name": record.get("asset_name", ""),
                    "type": record.get("asset_type", "")
                }
            })
        
        return regional_events
    
    except Exception as e:
        print(f"⚠️  Regional events 조회 중 에러: {e}")
        return []


def query_asset_factors(executor: QueryExecutor, asset_name: str) -> List[Dict]:
    """
    특정 Asset에 영향을 주는 Factor들 조회
    
    Args:
        executor: QueryExecutor 인스턴스
        asset_name: Asset 이름
    
    Returns:
        Asset에 영향을 주는 Factor 리스트
    """
    query = """
    MATCH (f:Factor)-[i:IMPACTS]->(a:Asset {name: $asset_name})
    OPTIONAL MATCH (e:Event)-[:TRIGGERS]->(f)
    RETURN f.name as factor_name, f.type as factor_type, f.value as factor_value,
           i.direction as impact_direction, i.magnitude as impact_magnitude, i.confidence as impact_confidence,
           a.name as asset_name, a.type as asset_type,
           collect(DISTINCT e.name) as triggering_events
    ORDER BY i.magnitude DESC
    LIMIT 10
    """
    
    try:
        result = executor.execute_query(query, {"asset_name": asset_name})
        
        factors = []
        for record in result.records:
            factors.append({
                "factor": {
                    "name": record.get("factor_name", ""),
                    "type": record.get("factor_type", ""),
                    "value": record.get("factor_value")
                },
                "impact": {
                    "direction": record.get("impact_direction", ""),
                    "magnitude": record.get("impact_magnitude", 0.0),
                    "confidence": record.get("impact_confidence", 0.0)
                },
                "asset": {
                    "name": record.get("asset_name", ""),
                    "type": record.get("asset_type", "")
                },
                "triggering_events": record.get("triggering_events", [])
            })
        
        return factors
    
    except Exception as e:
        print(f"⚠️  Asset factors 조회 중 에러: {e}")
        return []


@dataclass(frozen=True)
class EvidenceSource:
    id: int
    file: str
    page_number: int
    chunk_id: str
    excerpt: str
    original_sentence: str
    type: str = "neo4j"


class Neo4jRetriever:
    """
    질문에 대해 Neo4j에서 근거를 좁혀 가져오는 Retriever.

    반환은 UI/프롬프트에 쓰기 쉬운 sources 리스트와,
    디버깅/UX를 위한 evidence(문장-출처) 구조를 포함할 수 있음.
    """

    def __init__(self, executor: Optional[QueryExecutor] = None) -> None:
        self.executor = executor or QueryExecutor()
        self.entity_resolver = EntityResolver()
        self._cache: Dict[Tuple[str, int, int], Tuple[float, Dict]] = {}
        self._cache_ttl_sec = 60.0

    def close(self) -> None:
        try:
            self.executor.close()
        except Exception:
            pass

    def retrieve(
        self,
        question: str,
        depth: int = 2,
        limit: int = 50,
        top_sources: int = 10,
    ) -> Dict:
        """
        Returns:
            {
              "context": str,
              "sources": List[dict]
            }
        """
        cache_key = (question, depth, top_sources)
        now = time.time()
        cached = self._cache.get(cache_key)
        if cached and (now - cached[0]) < self._cache_ttl_sec:
            return cached[1]

        entity_terms = self._extract_entity_terms(question, max_terms=5)
        # 엔티티 후보가 없으면 질문 전체를 단일 term으로 처리
        if not entity_terms:
            entity_terms = [question.strip()[:64]]

        # 1) 엔티티 후보 노드 찾기 (Precision 우선: name contains, limit 낮게)
        seed_nodes = self._find_seed_nodes(entity_terms, limit=10)

        # 2) seed 노드 기준 2-hop+ 확장 (필터 + hard LIMIT)
        neighborhood = self._expand_neighborhood(seed_nodes, depth=depth, limit=limit)

        # 3) sources로 변환 (source_file/page/original_sentence 우선)
        sources = self._to_sources(neighborhood, top_sources=top_sources)

        context_lines: List[str] = []
        for s in sources:
            file_name = s.get("file", "Unknown")
            page = s.get("page_number", 0)
            original = s.get("original_sentence") or s.get("excerpt") or ""
            context_lines.append(f"[{s['id']}] {file_name} p.{page}: {original}")

        result = {
            "context": "\n".join(context_lines),
            "sources": sources,
        }
        self._cache[cache_key] = (now, result)
        return result

    def _extract_entity_terms(self, question: str, max_terms: int = 5) -> List[str]:
        # 간단한 휴리스틱: 대문자 토큰, 한글 2자 이상 토큰, 숫자/티커 제외
        raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9&._-]{1,}|[가-힣]{2,}", question)
        terms: List[str] = []
        for t in raw_tokens:
            if t.upper() in {"AND", "OR", "THE", "A", "AN"}:
                continue
            normalized = self.entity_resolver.normalize_entity(t)
            if normalized and normalized not in terms:
                terms.append(normalized)
            if len(terms) >= max_terms:
                break
        return terms

    def _find_seed_nodes(self, terms: List[str], limit: int = 10) -> List[Dict]:
        seeds: List[Dict] = []
        for term in terms:
            query = """
            MATCH (n:Entity)
            WHERE n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($term)
            RETURN n
            LIMIT $limit
            """
            result = self.executor.execute_query(query, parameters={"term": term, "limit": limit}, limit=limit)
            for node in result.nodes:
                # 중복 제거
                if any(s.get("id") == node.id for s in seeds):
                    continue
                seeds.append({"id": node.id, "name": getattr(node, "name", None), "type": getattr(node, "type", None)})
        return seeds[:limit]

    def _expand_neighborhood(self, seed_nodes: List[Dict], depth: int = 2, limit: int = 50) -> Neo4jQueryResult:
        if not seed_nodes:
            # 빈 결과
            return Neo4jQueryResult(nodes=[], relationships=[], count=0)

        seed_ids = [s["id"] for s in seed_nodes if s.get("id")]

        # depth는 1~3으로 제한
        depth = max(1, min(int(depth), 3))

        # 관계 확장: 1..depth hop, undirected
        # 필터: source_file이 있거나, original_sentence가 있는 것 우선(쿼리 단계에서 완전 필터는 위험)
        query = f"""
        MATCH (n:Entity)
        WHERE n.id IN $seed_ids
        MATCH p=(n)-[r*1..{depth}]-(m:Entity)
        WITH DISTINCT n, m, relationships(p) AS rels
        RETURN n AS a, m AS b, rels[0] AS r
        LIMIT $limit
        """
        return self.executor.execute_query(query, parameters={"seed_ids": seed_ids, "limit": limit}, limit=limit)

    def _to_sources(self, result: Neo4jQueryResult, top_sources: int = 10) -> List[Dict]:
        sources: List[EvidenceSource] = []

        def push_source(file_name: str, page: int, chunk_id: str, original: str) -> None:
            if not original:
                return
            # 중복 제거(같은 file/page/original)
            for s in sources:
                if s.file == file_name and s.page_number == page and s.original_sentence == original:
                    return
            excerpt = original[:300]
            sources.append(
                EvidenceSource(
                    id=len(sources) + 1,
                    file=file_name or "Unknown",
                    page_number=int(page) if isinstance(page, (int, float, str)) and str(page).isdigit() else 0,
                    chunk_id=str(chunk_id or ""),
                    excerpt=excerpt,
                    original_sentence=original,
                    type="neo4j",
                )
            )

        # 노드/관계 메타데이터에서 근거 수집
        for node in result.nodes:
            file_name = getattr(node, "source_file", "") or getattr(node, "source", "") or "Unknown"
            page = getattr(node, "page_number", 0) or 0
            original = getattr(node, "original_sentence", "") or getattr(node, "description", "") or ""
            push_source(file_name, page, getattr(node, "id", ""), original)

        for rel in result.relationships:
            file_name = getattr(rel, "source_file", "") or getattr(rel, "source", "") or "Unknown"
            page = getattr(rel, "page_number", 0) or 0
            original = getattr(rel, "original_sentence", "") or getattr(rel, "description", "") or ""
            chunk_id = f"{getattr(rel, 'source_id', '')}->{getattr(rel, 'target_id', '')}:{getattr(rel, 'type', '')}"
            push_source(file_name, page, chunk_id, original)

        # 상위 N개만 반환
        return [s.__dict__ for s in sources[:top_sources]]

