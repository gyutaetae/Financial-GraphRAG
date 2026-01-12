"""
Entity Classifier - Entity를 도메인 특화 노드로 분류하는 모듈

LLM을 활용하여 Entity를 Event/Actor/Asset/Factor/Region으로 분류합니다.
"""

import json
from typing import Dict, Optional, List
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, DOMAIN_CLASSIFICATION_MODEL


class EntityClassifier:
    """Entity를 Event/Actor/Asset/Factor/Region으로 분류"""
    
    CLASSIFICATION_PROMPT = """다음 엔티티를 금융 도메인 카테고리로 분류하세요.

엔티티 정보:
- 이름: {entity_name}
- 타입: {entity_type}
- 설명: {description}

분류 기준:
1. Event (사건): 금융 사건, 발표, 위기, 정책 변화
   예: "Fed 금리 인상", "SVB 파산", "중국 부동산 위기", "양적완화 발표"

2. Actor (주체): 기관, 정부, 기업, 인물
   예: "Federal Reserve", "중국 정부", "BlackRock", "제롬 파월"

3. Asset (자산): 투자 자산, 상품, 주식
   예: "금", "미국 부동산", "NVDA", "국채", "원유"

4. Factor (요인): 경제 지표, 시장 요인
   예: "금리", "달러 지수", "VIX", "인플레이션", "실업률"

5. Region (지역): 국가, 대륙, 시장
   예: "미국", "아시아", "신흥시장", "유럽", "중국"

6. None: 위 카테고리에 해당하지 않음

응답 형식 (JSON만):
{{"category": "Event/Actor/Asset/Factor/Region/None", "confidence": 0.0-1.0, "reasoning": "분류 이유"}}
"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        EntityClassifier 초기화
        
        Args:
            api_key: OpenAI API 키 (None이면 config에서 가져옴)
            model: 사용할 모델 (None이면 config에서 가져옴)
        """
        self.client = AsyncOpenAI(api_key=api_key or OPENAI_API_KEY)
        self.model = model or DOMAIN_CLASSIFICATION_MODEL
    
    async def classify_entity(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, str | float]:
        """
        Entity를 분류
        
        Args:
            entity_name: 엔티티 이름
            entity_type: 엔티티 타입 (옵션)
            description: 엔티티 설명 (옵션)
        
        Returns:
            분류 결과 딕셔너리
            {
                "category": "Event/Actor/Asset/Factor/Region/None",
                "confidence": 0.0-1.0,
                "reasoning": "분류 이유"
            }
        """
        try:
            # 프롬프트 생성
            prompt = self.CLASSIFICATION_PROMPT.format(
                entity_name=entity_name,
                entity_type=entity_type or "N/A",
                description=description or "N/A"
            )
            
            # LLM 호출
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 금융 엔티티를 정확하게 분류하는 전문가입니다. 반드시 JSON 형식으로만 응답하세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # 응답 파싱
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # 기본값 설정
            if "category" not in result:
                result["category"] = "None"
            if "confidence" not in result:
                result["confidence"] = 0.5
            if "reasoning" not in result:
                result["reasoning"] = "분류 이유 없음"
            
            return result
            
        except Exception as e:
            print(f"⚠️  Entity 분류 중 에러: {e}")
            return {
                "category": "None",
                "confidence": 0.0,
                "reasoning": f"분류 실패: {str(e)}"
            }
    
    async def classify_batch(
        self,
        entities: List[Dict[str, str]]
    ) -> List[Dict[str, str | float]]:
        """
        여러 Entity를 배치로 분류
        
        Args:
            entities: Entity 리스트
                [
                    {"name": "...", "type": "...", "description": "..."},
                    ...
                ]
        
        Returns:
            분류 결과 리스트
        """
        results = []
        
        for entity in entities:
            result = await self.classify_entity(
                entity_name=entity.get("name", ""),
                entity_type=entity.get("type"),
                description=entity.get("description")
            )
            
            # 원본 entity 정보와 결합
            result["entity_name"] = entity.get("name", "")
            result["entity_type"] = entity.get("type")
            
            results.append(result)
        
        return results
    
    def get_node_type_from_category(self, category: str) -> Optional[str]:
        """
        분류 카테고리를 Neo4j 노드 타입으로 변환
        
        Args:
            category: 분류 카테고리 (Event, Actor, Asset, Factor, Region, None)
        
        Returns:
            Neo4j 노드 타입 (Event, Actor, Asset, Factor, Region) 또는 None
        """
        valid_categories = ["Event", "Actor", "Asset", "Factor", "Region"]
        
        if category in valid_categories:
            return category
        else:
            return None
    
    def infer_node_properties(
        self,
        entity_name: str,
        category: str,
        entity_data: Optional[Dict] = None
    ) -> Dict[str, str | float]:
        """
        카테고리에 따라 노드 속성 추론
        
        Args:
            entity_name: 엔티티 이름
            category: 분류 카테고리
            entity_data: 추가 엔티티 데이터
        
        Returns:
            노드 속성 딕셔너리
        """
        entity_data = entity_data or {}
        
        base_properties = {
            "name": entity_name,
            "source": entity_data.get("source", "entity_classifier")
        }
        
        # 카테고리별 속성 추가
        if category == "Event":
            base_properties.update({
                "date": entity_data.get("date", ""),
                "description": entity_data.get("description", ""),
                "impact_level": entity_data.get("impact_level", "medium")
            })
        
        elif category == "Actor":
            # Actor 타입 추론
            actor_type = "company"  # 기본값
            name_lower = entity_name.lower()
            
            if any(keyword in name_lower for keyword in ["fed", "reserve", "bank", "중앙은행"]):
                actor_type = "central_bank"
            elif any(keyword in name_lower for keyword in ["정부", "government", "ministry"]):
                actor_type = "government"
            elif any(keyword in name_lower for keyword in ["fund", "capital", "investment"]):
                actor_type = "investor"
            
            base_properties.update({
                "type": entity_data.get("type", actor_type),
                "role": entity_data.get("role", "")
            })
        
        elif category == "Asset":
            # Asset 타입 추론
            asset_type = "stock"  # 기본값
            name_lower = entity_name.lower()
            
            if any(keyword in name_lower for keyword in ["금", "gold", "silver", "은"]):
                asset_type = "gold"
            elif any(keyword in name_lower for keyword in ["부동산", "real estate", "property"]):
                asset_type = "real_estate"
            elif any(keyword in name_lower for keyword in ["채권", "bond", "국채"]):
                asset_type = "bond"
            elif any(keyword in name_lower for keyword in ["원유", "oil", "commodity"]):
                asset_type = "commodity"
            
            base_properties.update({
                "type": entity_data.get("type", asset_type),
                "ticker": entity_data.get("ticker", "")
            })
        
        elif category == "Factor":
            # Factor 타입 추론
            factor_type = "interest_rate"  # 기본값
            name_lower = entity_name.lower()
            
            if any(keyword in name_lower for keyword in ["달러", "dollar", "dxy"]):
                factor_type = "dollar_index"
            elif any(keyword in name_lower for keyword in ["vix", "공포", "fear"]):
                factor_type = "fear_index"
            
            base_properties.update({
                "type": entity_data.get("type", factor_type),
                "value": entity_data.get("value"),
                "unit": entity_data.get("unit", "")
            })
        
        elif category == "Region":
            # Region 타입 추론
            region_type = "country"  # 기본값
            name_lower = entity_name.lower()
            
            if any(keyword in name_lower for keyword in ["아시아", "asia", "유럽", "europe"]):
                region_type = "continent"
            elif any(keyword in name_lower for keyword in ["시장", "market", "신흥"]):
                region_type = "market"
            
            # Region 코드 추론
            region_code = ""
            if "미국" in entity_name or "us" in name_lower:
                region_code = "US"
            elif "중국" in entity_name or "china" in name_lower:
                region_code = "CN"
            elif "아시아" in entity_name or "asia" in name_lower:
                region_code = "ASIA"
            
            base_properties.update({
                "type": entity_data.get("type", region_type),
                "code": entity_data.get("code", region_code)
            })
        
        return base_properties
