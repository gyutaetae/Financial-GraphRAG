"""
Relationship Inferencer - 도메인 관계 추론 엔진

LLM을 활용하여 Event, Actor, Asset, Factor, Region 간의 관계를 추론합니다.
- TRIGGERS: Event → Factor
- IMPACTS: Factor → Asset
- INVOLVED_IN: Actor → Event
- LOCATED_IN: Event → Region
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, DOMAIN_CLASSIFICATION_MODEL
from models.neo4j_models import (
    EventNode, ActorNode, AssetNode, FactorNode, RegionNode
)


class RelationshipInferencer:
    """도메인 관계 추론 (TRIGGERS, IMPACTS, INVOLVED_IN, LOCATED_IN)"""
    
    TRIGGERS_PROMPT = """다음 Event가 어떤 Factor들을 트리거(유발)하는지 분석하세요.

Event 정보:
- 이름: {event_name}
- 날짜: {event_date}
- 설명: {event_description}

가능한 Factor 목록:
{factors_list}

분석 기준:
- Event가 직접적으로 영향을 주는 Factor를 선택
- 인과관계가 명확한 경우만 포함
- 신뢰도는 0.0~1.0 (높을수록 확실)

응답 형식 (JSON만):
{{
  "relationships": [
    {{
      "factor_id": "factor_id",
      "factor_name": "factor_name",
      "confidence": 0.0-1.0,
      "reasoning": "인과관계 설명"
    }}
  ]
}}
"""
    
    IMPACTS_PROMPT = """다음 Factor가 어떤 Asset들에 영향을 주는지 분석하세요.

Factor 정보:
- 이름: {factor_name}
- 타입: {factor_type}
- 값: {factor_value}

가능한 Asset 목록:
{assets_list}

분석 기준:
- Factor가 Asset에 미치는 영향 방향 (Positive/Negative)
- 영향 크기 (magnitude: 0.0~1.0)
- 신뢰도 (confidence: 0.0~1.0)

응답 형식 (JSON만):
{{
  "relationships": [
    {{
      "asset_id": "asset_id",
      "asset_name": "asset_name",
      "direction": "Positive/Negative",
      "magnitude": 0.0-1.0,
      "confidence": 0.0-1.0,
      "reasoning": "영향 설명"
    }}
  ]
}}
"""
    
    INVOLVED_IN_PROMPT = """다음 Actor들이 Event에 어떻게 관여했는지 분석하세요.

Event 정보:
- 이름: {event_name}
- 날짜: {event_date}
- 설명: {event_description}

가능한 Actor 목록:
{actors_list}

분석 기준:
- Actor가 Event에서 수행한 역할
- 영향력 수준 (high, medium, low)
- 신뢰도 (0.0~1.0)

응답 형식 (JSON만):
{{
  "relationships": [
    {{
      "actor_id": "actor_id",
      "actor_name": "actor_name",
      "role": "역할 설명",
      "influence_level": "high/medium/low",
      "confidence": 0.0-1.0,
      "reasoning": "관여 설명"
    }}
  ]
}}
"""
    
    LOCATED_IN_PROMPT = """다음 Event가 어떤 Region에서 발생했는지 분석하세요.

Event 정보:
- 이름: {event_name}
- 날짜: {event_date}
- 설명: {event_description}

가능한 Region 목록:
{regions_list}

분석 기준:
- Event가 발생한 지역
- 영향 범위 (local, regional, global)
- 신뢰도 (0.0~1.0)

응답 형식 (JSON만):
{{
  "relationships": [
    {{
      "region_id": "region_id",
      "region_name": "region_name",
      "impact_scope": "local/regional/global",
      "confidence": 0.0-1.0,
      "reasoning": "지역 설명"
    }}
  ]
}}
"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        RelationshipInferencer 초기화
        
        Args:
            api_key: OpenAI API 키
            model: 사용할 모델
        """
        self.client = AsyncOpenAI(api_key=api_key or OPENAI_API_KEY)
        self.model = model or DOMAIN_CLASSIFICATION_MODEL
    
    async def infer_triggers(
        self,
        event: Dict[str, str],
        factors: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Event가 어떤 Factor를 트리거하는지 추론
        
        Args:
            event: Event 정보 딕셔너리
            factors: Factor 리스트
        
        Returns:
            TRIGGERS 관계 리스트
        """
        try:
            # Factor 목록 포맷팅
            factors_list = "\n".join([
                f"- ID: {f.get('id', '')}, 이름: {f.get('name', '')}, 타입: {f.get('type', '')}"
                for f in factors
            ])
            
            # 프롬프트 생성
            prompt = self.TRIGGERS_PROMPT.format(
                event_name=event.get("name", ""),
                event_date=event.get("date", "N/A"),
                event_description=event.get("description", "N/A"),
                factors_list=factors_list
            )
            
            # LLM 호출
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 금융 이벤트와 요인 간의 인과관계를 분석하는 전문가입니다. 반드시 JSON 형식으로만 응답하세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            # 응답 파싱
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # 관계 데이터 생성
            relationships = []
            for rel in result.get("relationships", []):
                relationships.append({
                    "type": "TRIGGERS",
                    "source_id": event.get("id", ""),
                    "target_id": rel.get("factor_id", ""),
                    "source_label": "Event",
                    "target_label": "Factor",
                    "confidence": rel.get("confidence", 0.5),
                    "timestamp": datetime.now().isoformat(),
                    "source": "relationship_inferencer",
                    "reasoning": rel.get("reasoning", "")
                })
            
            return relationships
            
        except Exception as e:
            print(f"⚠️  TRIGGERS 관계 추론 중 에러: {e}")
            return []
    
    async def infer_impacts(
        self,
        factor: Dict[str, str | float],
        assets: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Factor가 어떤 Asset에 영향을 주는지 추론 (방향 포함)
        
        Args:
            factor: Factor 정보 딕셔너리
            assets: Asset 리스트
        
        Returns:
            IMPACTS 관계 리스트
        """
        try:
            # Asset 목록 포맷팅
            assets_list = "\n".join([
                f"- ID: {a.get('id', '')}, 이름: {a.get('name', '')}, 타입: {a.get('type', '')}"
                for a in assets
            ])
            
            # 프롬프트 생성
            prompt = self.IMPACTS_PROMPT.format(
                factor_name=factor.get("name", ""),
                factor_type=factor.get("type", "N/A"),
                factor_value=factor.get("value", "N/A"),
                assets_list=assets_list
            )
            
            # LLM 호출
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 금융 요인이 자산에 미치는 영향을 분석하는 전문가입니다. 반드시 JSON 형식으로만 응답하세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            # 응답 파싱
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # 관계 데이터 생성
            relationships = []
            for rel in result.get("relationships", []):
                relationships.append({
                    "type": "IMPACTS",
                    "source_id": factor.get("id", ""),
                    "target_id": rel.get("asset_id", ""),
                    "source_label": "Factor",
                    "target_label": "Asset",
                    "direction": rel.get("direction", "Positive"),
                    "magnitude": rel.get("magnitude", 0.5),
                    "confidence": rel.get("confidence", 0.5),
                    "timestamp": datetime.now().isoformat(),
                    "source": "relationship_inferencer",
                    "reasoning": rel.get("reasoning", "")
                })
            
            return relationships
            
        except Exception as e:
            print(f"⚠️  IMPACTS 관계 추론 중 에러: {e}")
            return []
    
    async def infer_involved_in(
        self,
        actors: List[Dict[str, str]],
        event: Dict[str, str]
    ) -> List[Dict]:
        """
        어떤 Actor가 Event에 관여했는지 추론
        
        Args:
            actors: Actor 리스트
            event: Event 정보 딕셔너리
        
        Returns:
            INVOLVED_IN 관계 리스트
        """
        try:
            # Actor 목록 포맷팅
            actors_list = "\n".join([
                f"- ID: {a.get('id', '')}, 이름: {a.get('name', '')}, 타입: {a.get('type', '')}"
                for a in actors
            ])
            
            # 프롬프트 생성
            prompt = self.INVOLVED_IN_PROMPT.format(
                event_name=event.get("name", ""),
                event_date=event.get("date", "N/A"),
                event_description=event.get("description", "N/A"),
                actors_list=actors_list
            )
            
            # LLM 호출
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 금융 이벤트에 관여한 주체를 분석하는 전문가입니다. 반드시 JSON 형식으로만 응답하세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            # 응답 파싱
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # 관계 데이터 생성
            relationships = []
            for rel in result.get("relationships", []):
                relationships.append({
                    "type": "INVOLVED_IN",
                    "source_id": rel.get("actor_id", ""),
                    "target_id": event.get("id", ""),
                    "source_label": "Actor",
                    "target_label": "Event",
                    "role": rel.get("role", ""),
                    "influence_level": rel.get("influence_level", "medium"),
                    "timestamp": datetime.now().isoformat(),
                    "source": "relationship_inferencer",
                    "reasoning": rel.get("reasoning", "")
                })
            
            return relationships
            
        except Exception as e:
            print(f"⚠️  INVOLVED_IN 관계 추론 중 에러: {e}")
            return []
    
    async def infer_located_in(
        self,
        event: Dict[str, str],
        regions: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Event가 어떤 Region에서 발생했는지 추론
        
        Args:
            event: Event 정보 딕셔너리
            regions: Region 리스트
        
        Returns:
            LOCATED_IN 관계 리스트
        """
        try:
            # Region 목록 포맷팅
            regions_list = "\n".join([
                f"- ID: {r.get('id', '')}, 이름: {r.get('name', '')}, 타입: {r.get('type', '')}"
                for r in regions
            ])
            
            # 프롬프트 생성
            prompt = self.LOCATED_IN_PROMPT.format(
                event_name=event.get("name", ""),
                event_date=event.get("date", "N/A"),
                event_description=event.get("description", "N/A"),
                regions_list=regions_list
            )
            
            # LLM 호출
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 금융 이벤트의 발생 지역을 분석하는 전문가입니다. 반드시 JSON 형식으로만 응답하세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            # 응답 파싱
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # 관계 데이터 생성
            relationships = []
            for rel in result.get("relationships", []):
                relationships.append({
                    "type": "LOCATED_IN",
                    "source_id": event.get("id", ""),
                    "target_id": rel.get("region_id", ""),
                    "source_label": "Event",
                    "target_label": "Region",
                    "impact_scope": rel.get("impact_scope", "regional"),
                    "timestamp": datetime.now().isoformat(),
                    "source": "relationship_inferencer",
                    "reasoning": rel.get("reasoning", "")
                })
            
            return relationships
            
        except Exception as e:
            print(f"⚠️  LOCATED_IN 관계 추론 중 에러: {e}")
            return []
    
    async def infer_all_relationships(
        self,
        events: List[Dict],
        actors: List[Dict],
        assets: List[Dict],
        factors: List[Dict],
        regions: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        모든 도메인 관계를 한 번에 추론
        
        Args:
            events: Event 리스트
            actors: Actor 리스트
            assets: Asset 리스트
            factors: Factor 리스트
            regions: Region 리스트
        
        Returns:
            관계 타입별 관계 리스트 딕셔너리
        """
        all_relationships = {
            "TRIGGERS": [],
            "IMPACTS": [],
            "INVOLVED_IN": [],
            "LOCATED_IN": []
        }
        
        # Event → Factor (TRIGGERS)
        for event in events:
            triggers = await self.infer_triggers(event, factors)
            all_relationships["TRIGGERS"].extend(triggers)
        
        # Factor → Asset (IMPACTS)
        for factor in factors:
            impacts = await self.infer_impacts(factor, assets)
            all_relationships["IMPACTS"].extend(impacts)
        
        # Actor → Event (INVOLVED_IN)
        for event in events:
            involved = await self.infer_involved_in(actors, event)
            all_relationships["INVOLVED_IN"].extend(involved)
        
        # Event → Region (LOCATED_IN)
        for event in events:
            located = await self.infer_located_in(event, regions)
            all_relationships["LOCATED_IN"].extend(located)
        
        return all_relationships
