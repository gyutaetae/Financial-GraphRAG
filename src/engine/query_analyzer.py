"""
Enhanced Query Analyzer for Risk and Comprehensive Queries
Uses LLM to extract entities, intent, and generate graph exploration strategies
"""

import json
from typing import Dict, List, Optional, Tuple
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_BASE_URL


class QueryAnalyzer:
    """
    LLM-powered query analyzer for comprehensive risk analysis
    Extracts: entities, intent, risk categories, graph exploration strategy
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        self.model = "gpt-4o-mini"
    
    async def analyze_query(self, question: str) -> Dict:
        """
        Analyze user query to extract:
        - Core entities (e.g., "Nvidia")
        - Intent (e.g., "risk", "opportunity", "financial performance")
        - Risk categories if applicable
        - Graph exploration strategy
        
        Args:
            question: User question (e.g., "Nvidia's risk")
        
        Returns:
            {
                "entities": ["Nvidia"],
                "intent": "risk_analysis",
                "risk_categories": ["geopolitical", "supply_chain", "competition"],
                "exploration_strategy": {
                    "max_hops": 2,
                    "priority_relationships": ["IMPACTS", "DEPENDS_ON", "COMPETES_WITH"],
                    "focus_nodes": ["Company", "Country", "Industry", "MacroIndicator"]
                },
                "requires_synthesis": true
            }
        """
        
        system_prompt = """You are a financial analyst AI that analyzes user queries about companies and markets.

Your task: Extract structured information from user questions for knowledge graph exploration.

Output JSON with:
1. "entities": List of company/entity names mentioned
2. "intent": One of ["risk_analysis", "opportunity", "financial_performance", "market_position", "general_info"]
3. "risk_categories": If intent is risk_analysis, list applicable categories:
   - "geopolitical": Political/regulatory risks
   - "supply_chain": Supplier/manufacturing risks
   - "competition": Market competition risks
   - "financial": Financial/debt risks
   - "technology": Technology/innovation risks
4. "exploration_strategy":
   - "max_hops": 1-3 (how far to explore in graph)
   - "priority_relationships": Which edge types to prioritize
   - "focus_nodes": Which node types are most relevant
5. "requires_synthesis": true if needs multi-source integration

Examples:
Q: "Nvidia's risk"
A: {
  "entities": ["Nvidia"],
  "intent": "risk_analysis",
  "risk_categories": ["geopolitical", "supply_chain", "competition"],
  "exploration_strategy": {
    "max_hops": 2,
    "priority_relationships": ["IMPACTS", "DEPENDS_ON", "COMPETES_WITH", "LOCATED_IN"],
    "focus_nodes": ["Company", "Country", "Industry", "MacroIndicator", "Supplier"]
  },
  "requires_synthesis": true
}

Q: "Apple revenue"
A: {
  "entities": ["Apple"],
  "intent": "financial_performance",
  "risk_categories": [],
  "exploration_strategy": {
    "max_hops": 1,
    "priority_relationships": ["HAS_METRIC"],
    "focus_nodes": ["Company", "FinancialMetric"]
  },
  "requires_synthesis": false
}"""

        user_message = f"Question: {question}\n\nAnalyze this query and return JSON."
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            print(f"📊 Query Analysis: {result}")
            return result
            
        except Exception as e:
            print(f"⚠️  Query analysis failed: {e}")
            # Fallback: simple parsing
            return self._fallback_analysis(question)
    
    def _fallback_analysis(self, question: str) -> Dict:
        """Simple fallback when LLM fails"""
        q_lower = question.lower()
        
        # Detect intent
        intent = "general_info"
        if "risk" in q_lower or "threat" in q_lower or "vulnerability" in q_lower:
            intent = "risk_analysis"
        elif "revenue" in q_lower or "profit" in q_lower or "financial" in q_lower:
            intent = "financial_performance"
        elif "opportunity" in q_lower or "growth" in q_lower:
            intent = "opportunity"
        
        # Detect entities (simple word extraction)
        entities = []
        common_companies = ["nvidia", "apple", "google", "microsoft", "tsmc", "intel", "amd"]
        for company in common_companies:
            if company in q_lower:
                entities.append(company.capitalize())
        
        # Risk categories for risk intent
        risk_categories = []
        if intent == "risk_analysis":
            risk_categories = ["geopolitical", "supply_chain", "competition"]
        
        return {
            "entities": entities if entities else ["Unknown"],
            "intent": intent,
            "risk_categories": risk_categories,
            "exploration_strategy": {
                "max_hops": 2 if intent == "risk_analysis" else 1,
                "priority_relationships": ["IMPACTS", "DEPENDS_ON", "COMPETES_WITH"],
                "focus_nodes": ["Company", "Country", "Industry"]
            },
            "requires_synthesis": intent == "risk_analysis"
        }
    
    def generate_cypher_exploration_query(
        self, 
        entities: List[str], 
        strategy: Dict
    ) -> str:
        """
        Generate Cypher query for graph exploration based on strategy
        
        Args:
            entities: Core entities to explore from
            strategy: exploration_strategy from analyze_query
        
        Returns:
            Cypher query string
        """
        max_hops = strategy.get("max_hops", 2)
        priority_rels = strategy.get("priority_relationships", [])
        focus_nodes = strategy.get("focus_nodes", [])
        
        # Build relationship filter
        rel_filter = ""
        if priority_rels:
            rel_types = "|".join(priority_rels)
            rel_filter = f":{rel_types}"
        
        # Build node label filter for end nodes
        node_filter = ""
        if focus_nodes:
            node_labels = "|".join(focus_nodes)
            node_filter = f":{node_labels}"
        
        entity_pattern = "|".join([f"(?i).*{e}.*" for e in entities])
        
        # Generate multi-hop path query
        if max_hops == 1:
            query = f"""
            MATCH (start {{name: ~'{entity_pattern}'}})-[r{rel_filter}]->(end{node_filter})
            RETURN 
                start.name AS source,
                type(r) AS relationship,
                end.name AS target,
                end AS targetNode,
                properties(r) AS relProps
            LIMIT 50
            """
        else:
            # 2+ hop exploration
            query = f"""
            MATCH path = (start {{name: ~'{entity_pattern}'}})-[*1..{max_hops}]->(end{node_filter})
            WHERE ALL(r IN relationships(path) WHERE type(r) IN [{', '.join([f"'{r}'" for r in priority_rels])}])
            WITH path, start, end, 
                 [r IN relationships(path) | type(r)] AS relTypes,
                 [n IN nodes(path) | n.name] AS nodeNames
            RETURN 
                start.name AS source,
                relTypes AS pathRelationships,
                nodeNames AS pathNodes,
                end.name AS target,
                end AS targetNode,
                length(path) AS pathLength
            ORDER BY pathLength ASC
            LIMIT 100
            """
        
        return query.strip()
    
    def classify_risks_from_paths(
        self, 
        paths: List[Dict],
        risk_categories: List[str]
    ) -> Dict[str, List[str]]:
        """
        Classify discovered paths into risk categories
        
        Args:
            paths: List of graph paths from Cypher query
            risk_categories: Target risk categories
        
        Returns:
            {
                "geopolitical": ["Nvidia → Taiwan → China Conflict"],
                "supply_chain": ["Nvidia → TSMC → Semiconductor Shortage"],
                ...
            }
        """
        classified = {category: [] for category in risk_categories}
        
        # Keyword-based classification
        geo_keywords = ["country", "government", "regulation", "conflict", "sanctions", "taiwan", "china"]
        supply_keywords = ["supplier", "manufacturing", "shortage", "disruption", "tsmc", "supply"]
        competition_keywords = ["competitor", "market", "amd", "intel", "share"]
        
        for path in paths:
            path_str = str(path).lower()
            
            if "geopolitical" in risk_categories:
                if any(kw in path_str for kw in geo_keywords):
                    classified["geopolitical"].append(self._format_path(path))
            
            if "supply_chain" in risk_categories:
                if any(kw in path_str for kw in supply_keywords):
                    classified["supply_chain"].append(self._format_path(path))
            
            if "competition" in risk_categories:
                if any(kw in path_str for kw in competition_keywords):
                    classified["competition"].append(self._format_path(path))
        
        return classified
    
    def _format_path(self, path: Dict) -> str:
        """Format a graph path for readability"""
        if "pathNodes" in path:
            nodes = path["pathNodes"]
            return " → ".join(nodes)
        elif "source" in path and "target" in path:
            rel = path.get("relationship", "RELATED_TO")
            return f"{path['source']} --{rel}--> {path['target']}"
        else:
            return str(path)
    
    async def build_risk_context(
        self,
        entities: List[str],
        classified_risks: Dict[str, List[str]],
        raw_paths: List[Dict]
    ) -> str:
        """
        Build comprehensive context text for final LLM answer generation
        
        Args:
            entities: Core entities
            classified_risks: Risks by category
            raw_paths: Raw graph paths
        
        Returns:
            Formatted context string
        """
        context_parts = [
            f"# Risk Analysis Context for: {', '.join(entities)}\n"
        ]
        
        for category, paths in classified_risks.items():
            if paths:
                context_parts.append(f"\n## {category.replace('_', ' ').title()} Risks")
                for i, path in enumerate(paths[:5], 1):  # Limit to top 5 per category
                    context_parts.append(f"{i}. {path}")
        
        # Add raw paths summary
        if raw_paths:
            context_parts.append("\n## Additional Connections")
            for path in raw_paths[:10]:
                formatted = self._format_path(path)
                context_parts.append(f"- {formatted}")
        
        return "\n".join(context_parts)
