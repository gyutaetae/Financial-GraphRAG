"""
Privacy Analyst Agent
LangChain-based agent for analyzing company data with 2-hop graph traversal
Provides insights on supply chain risks, talent flow, and hidden relationships
"""

import asyncio
from typing import Dict, List, Any, Optional
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import OLLAMA_BASE_URL, LOCAL_MODELS

# Try to import LangChain components
try:
    from langchain.memory import ConversationBufferMemory
    from langchain.agents import Tool, AgentExecutor, create_react_agent
    from langchain.prompts import PromptTemplate
    from langchain_community.chat_models import ChatOllama
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️  LangChain not installed. Agent functionality limited.")
    print("💡 Install with: pip install langchain langchain-community")

try:
    from ollama import AsyncClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️  ollama not installed.")


class PrivacyAnalystAgent:
    """
    Privacy-First Analyst Agent using LangChain
    Analyzes company data using Neo4j 2-hop traversal for insights
    """
    
    def __init__(self, neo4j_db=None, neo4j_retriever=None):
        """
        Initialize analyst agent
        
        Args:
            neo4j_db: Neo4jDatabase instance
            neo4j_retriever: Neo4jRetriever instance with 2-hop support
        """
        self.neo4j_db = neo4j_db
        self.neo4j_retriever = neo4j_retriever
        self.ollama_client = AsyncClient(host=OLLAMA_BASE_URL) if OLLAMA_AVAILABLE else None
        self.llm_model = LOCAL_MODELS["llm"]
        
        # Initialize LangChain components if available
        if LANGCHAIN_AVAILABLE:
            self.llm = ChatOllama(
                model=self.llm_model,
                base_url=OLLAMA_BASE_URL,
                temperature=0.3
            )
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            self._setup_tools()
        else:
            self.llm = None
            self.memory = None
    
    def _setup_tools(self):
        """Setup tools for the agent"""
        self.tools = [
            Tool(
                name="neo4j_search",
                func=self._neo4j_search_sync,
                description="Search for entities in the Neo4j graph database by name or type. Input should be a search term."
            ),
            Tool(
                name="two_hop_explore",
                func=self._two_hop_explore_sync,
                description="Explore 2-hop relationships from given entity names to find hidden connections. Input should be comma-separated entity names."
            ),
            Tool(
                name="supply_chain_risk",
                func=self._supply_chain_risk_sync,
                description="Analyze supply chain risks for a company. Input should be a company name."
            ),
            Tool(
                name="talent_flow_analysis",
                func=self._talent_flow_sync,
                description="Analyze talent flow between companies. Input should be a company name."
            )
        ]
    
    async def neo4j_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Neo4j for entities matching query
        
        Args:
            query: Search term
            
        Returns:
            List of matching nodes
        """
        if not self.neo4j_db:
            return []
        
        cypher = """
MATCH (n)
WHERE toLower(n.name) CONTAINS toLower($query)
RETURN n.name AS name, labels(n)[0] AS type, properties(n) AS properties
LIMIT 20
"""
        
        try:
            results = self.neo4j_db.execute_query(cypher, {"query": query})
            return results
        except Exception as e:
            print(f"⚠️  Neo4j search error: {e}")
            return []
    
    def _neo4j_search_sync(self, query: str) -> str:
        """Synchronous wrapper for neo4j_search"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(self.neo4j_search(query))
        loop.close()
        
        if not results:
            return f"No entities found matching '{query}'"
        
        output = f"Found {len(results)} entities:\n"
        for r in results:
            output += f"- {r['name']} ({r['type']})\n"
        return output
    
    async def two_hop_explore(self, entity_names: List[str]) -> Dict[str, Any]:
        """
        Explore 2-hop relationships from given entities
        
        Args:
            entity_names: List of entity names to start from
            
        Returns:
            Dict with paths and insights
        """
        if not self.neo4j_db:
            return {"paths": [], "insights": []}
        
        cypher = """
MATCH path = (start)-[r1]->(mid)-[r2]->(end)
WHERE start.name IN $names
RETURN 
    start.name AS start_name,
    type(r1) AS rel1_type,
    mid.name AS mid_name,
    labels(mid)[0] AS mid_type,
    type(r2) AS rel2_type,
    end.name AS end_name,
    labels(end)[0] AS end_type
LIMIT 100
"""
        
        try:
            results = self.neo4j_db.execute_query(cypher, {"names": entity_names})
            
            # Analyze patterns
            insights = self._analyze_patterns(results)
            
            return {
                "paths": results,
                "insights": insights,
                "count": len(results)
            }
        except Exception as e:
            print(f"⚠️  2-hop exploration error: {e}")
            return {"paths": [], "insights": [], "count": 0}
    
    def _two_hop_explore_sync(self, entity_names: str) -> str:
        """Synchronous wrapper for two_hop_explore"""
        names = [n.strip() for n in entity_names.split(",")]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.two_hop_explore(names))
        loop.close()
        
        if result["count"] == 0:
            return f"No 2-hop paths found from {entity_names}"
        
        output = f"Found {result['count']} 2-hop paths:\n\n"
        
        # Show sample paths
        for path in result["paths"][:5]:
            output += f"  {path['start_name']} --[{path['rel1_type']}]--> "
            output += f"{path['mid_name']} ({path['mid_type']}) --[{path['rel2_type']}]--> "
            output += f"{path['end_name']} ({path['end_type']})\n"
        
        if result["insights"]:
            output += f"\n🔍 Insights:\n"
            for insight in result["insights"]:
                output += f"  - {insight}\n"
        
        return output
    
    def _analyze_patterns(self, paths: List[Dict]) -> List[str]:
        """
        Analyze 2-hop patterns for insights
        
        Args:
            paths: List of 2-hop path results
            
        Returns:
            List of insight strings
        """
        insights = []
        
        # Supply chain risk patterns
        debt_suppliers = [p for p in paths if "SUPPLIES" in p.get("rel1_type", "") and "HAS_DEBT" in p.get("rel2_type", "")]
        if debt_suppliers:
            insights.append(f"Supply Chain Risk: {len(debt_suppliers)} suppliers with debt detected")
        
        # Talent flow patterns
        talent_flow = [p for p in paths if "LOST_EMPLOYEE" in p.get("rel1_type", "") and "JOINED" in p.get("rel2_type", "")]
        if talent_flow:
            companies = set(p["end_name"] for p in talent_flow)
            insights.append(f"Talent Flow: Employees moved to {len(companies)} competitors")
        
        # Investment patterns
        investments = [p for p in paths if "INVESTS_IN" in p.get("rel1_type", "") or "INVESTS_IN" in p.get("rel2_type", "")]
        if investments:
            insights.append(f"Investment Network: {len(investments)} investment relationships found")
        
        # Geographic patterns
        locations = [p for p in paths if "LOCATED_IN" in p.get("rel2_type", "") or "OPERATES_IN" in p.get("rel2_type", "")]
        if locations:
            regions = set(p["end_name"] for p in locations)
            insights.append(f"Geographic Presence: Operations in {len(regions)} regions")
        
        return insights
    
    async def supply_chain_risk_analysis(self, company_name: str) -> Dict[str, Any]:
        """
        Analyze supply chain risks for a company
        
        Args:
            company_name: Name of company to analyze
            
        Returns:
            Risk analysis results
        """
        if not self.neo4j_db:
            return {"risk_level": "unknown", "details": []}
        
        cypher = """
MATCH (company {name: $company_name})-[:SUPPLIES|PURCHASES*1..2]-(supplier)
OPTIONAL MATCH (supplier)-[:HAS_DEBT|HAS_RISK]-(risk)
RETURN 
    supplier.name AS supplier_name,
    labels(supplier)[0] AS supplier_type,
    COLLECT(DISTINCT risk.name) AS risks
LIMIT 50
"""
        
        try:
            results = self.neo4j_db.execute_query(cypher, {"company_name": company_name})
            
            risk_count = sum(1 for r in results if r.get("risks"))
            risk_level = "high" if risk_count > 3 else "medium" if risk_count > 0 else "low"
            
            return {
                "risk_level": risk_level,
                "suppliers_analyzed": len(results),
                "at_risk_suppliers": risk_count,
                "details": results
            }
        except Exception as e:
            print(f"⚠️  Supply chain analysis error: {e}")
            return {"risk_level": "unknown", "details": []}
    
    def _supply_chain_risk_sync(self, company_name: str) -> str:
        """Synchronous wrapper for supply_chain_risk_analysis"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.supply_chain_risk_analysis(company_name))
        loop.close()
        
        output = f"Supply Chain Risk Analysis for {company_name}:\n"
        output += f"  Risk Level: {result['risk_level'].upper()}\n"
        output += f"  Suppliers Analyzed: {result.get('suppliers_analyzed', 0)}\n"
        output += f"  At-Risk Suppliers: {result.get('at_risk_suppliers', 0)}\n"
        
        return output
    
    async def talent_flow_analysis(self, company_name: str) -> Dict[str, Any]:
        """
        Analyze talent flow for a company
        
        Args:
            company_name: Name of company to analyze
            
        Returns:
            Talent flow analysis results
        """
        if not self.neo4j_db:
            return {"inflow": 0, "outflow": 0, "details": []}
        
        cypher = """
MATCH (company {name: $company_name})
OPTIONAL MATCH (company)-[:LOST_EMPLOYEE]->(person)-[:JOINED]->(competitor)
WITH company, COLLECT({person: person.name, to: competitor.name}) AS outflow_data
OPTIONAL MATCH (competitor)-[:LOST_EMPLOYEE]->(person)-[:JOINED]->(company)
WITH company, outflow_data, COLLECT({person: person.name, from: competitor.name}) AS inflow_data
RETURN 
    SIZE(outflow_data) AS outflow,
    SIZE(inflow_data) AS inflow,
    outflow_data,
    inflow_data
"""
        
        try:
            results = self.neo4j_db.execute_query(cypher, {"company_name": company_name})
            
            if results:
                return results[0]
            return {"inflow": 0, "outflow": 0, "details": []}
        except Exception as e:
            print(f"⚠️  Talent flow analysis error: {e}")
            return {"inflow": 0, "outflow": 0, "details": []}
    
    def _talent_flow_sync(self, company_name: str) -> str:
        """Synchronous wrapper for talent_flow_analysis"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.talent_flow_analysis(company_name))
        loop.close()
        
        output = f"Talent Flow Analysis for {company_name}:\n"
        output += f"  Incoming: {result.get('inflow', 0)} employees\n"
        output += f"  Outgoing: {result.get('outflow', 0)} employees\n"
        
        net = result.get('inflow', 0) - result.get('outflow', 0)
        if net > 0:
            output += f"  Net Gain: +{net} employees\n"
        elif net < 0:
            output += f"  Net Loss: {net} employees\n"
        
        return output
    
    async def analyze(self, query: str) -> str:
        """
        Main analysis method using LangChain agent
        
        Args:
            query: User query
            
        Returns:
            Analysis result
        """
        if not LANGCHAIN_AVAILABLE or not self.llm:
            # Fallback to simple analysis
            return await self._simple_analyze(query)
        
        # Create agent prompt
        template = """You are a business analyst with access to a graph database.
Answer the user's question by using the available tools.

Available tools:
{tools}

Tool names: {tool_names}

Question: {input}

Thought: {agent_scratchpad}
"""
        
        prompt = PromptTemplate.from_template(template)
        
        try:
            # Create and run agent
            agent = create_react_agent(self.llm, self.tools, prompt)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                max_iterations=5,
                handle_parsing_errors=True
            )
            
            result = await agent_executor.ainvoke({"input": query})
            return result.get("output", "Unable to generate analysis.")
            
        except Exception as e:
            print(f"⚠️  Agent execution error: {e}")
            return await self._simple_analyze(query)
    
    async def _simple_analyze(self, query: str) -> str:
        """
        Simple fallback analysis without LangChain
        
        Args:
            query: User query
            
        Returns:
            Analysis result
        """
        # Search for entities mentioned in query
        words = query.lower().split()
        potential_entities = [w for w in words if len(w) > 3]
        
        results = []
        for entity in potential_entities[:3]:  # Limit to 3 entities
            search_results = await self.neo4j_search(entity)
            if search_results:
                results.extend(search_results)
        
        if not results:
            return "No relevant entities found in the database."
        
        # Simple analysis using Ollama
        if self.ollama_client:
            context = "Entities found:\n"
            for r in results[:5]:
                context += f"- {r['name']} ({r['type']})\n"
            
            prompt = f"{context}\n\nUser question: {query}\n\nProvide a brief analysis:"
            
            try:
                response = await self.ollama_client.chat(
                    model=self.llm_model,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response['message']['content']
            except Exception as e:
                print(f"⚠️  Ollama error: {e}")
        
        # Final fallback
        return f"Found {len(results)} relevant entities. Please refine your query."


# Test function
async def test_analyst():
    """Test function for development"""
    print("\n=== Testing Privacy Analyst Agent ===")
    
    agent = PrivacyAnalystAgent(neo4j_db=None)
    
    # Test simple query
    result = await agent.analyze("What companies are in the database?")
    print(f"\nResult: {result}")
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_analyst())
