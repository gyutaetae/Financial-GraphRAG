#!/usr/bin/env python3
"""Simple seed data script using Neo4j driver directly"""

import sys
import os
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

def run_query(driver, query):
    with driver.session() as session:
        result = session.run(query)
        return list(result)

def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    print("✅ Connected to Neo4j")
    
    # Countries
    queries = [
        "MERGE (c:Country {name: 'United States'}) SET c.region = 'North America'",
        "MERGE (c:Country {name: 'China'}) SET c.region = 'Asia'",
        "MERGE (c:Country {name: 'Taiwan'}) SET c.region = 'Asia'",
        "MERGE (c:Country {name: 'Vietnam'}) SET c.region = 'Southeast Asia'",
        
        # Industries
        "MERGE (i:Industry {name: 'Semiconductor'}) SET i.sector = 'Technology'",
        "MERGE (i:Industry {name: 'Artificial Intelligence'}) SET i.sector = 'Technology'",
        
        # Macro Indicators
        "MERGE (m:MacroIndicator {name: 'US-China Trade War'}) SET m.type = 'geopolitical', m.impact_level = 'high'",
        "MERGE (m:MacroIndicator {name: 'Taiwan Strait Tension'}) SET m.type = 'geopolitical', m.impact_level = 'critical'",
        "MERGE (m:MacroIndicator {name: 'Global Semiconductor Shortage'}) SET m.type = 'supply_chain'",
        
        # Companies
        "MERGE (c:Company {name: 'Nvidia'}) SET c.market_cap = 1200, c.revenue = 60.9, c.country = 'United States'",
        "MERGE (c:Company {name: 'TSMC'}) SET c.market_cap = 500, c.revenue = 69.3, c.country = 'Taiwan'",
        "MERGE (c:Company {name: 'AMD'}) SET c.market_cap = 240, c.revenue = 22.7, c.country = 'United States'",
        "MERGE (c:Company {name: 'FPT Semiconductor'}) SET c.market_cap = 15, c.revenue = 4.5, c.country = 'Vietnam', c.industry = 'Semiconductor Manufacturing'",
        
        # Company → Industry
        "MATCH (c:Company {name: 'Nvidia'}), (i:Industry {name: 'Semiconductor'}) MERGE (c)-[:OPERATES_IN]->(i)",
        "MATCH (c:Company {name: 'TSMC'}), (i:Industry {name: 'Semiconductor'}) MERGE (c)-[:OPERATES_IN]->(i)",
        "MATCH (c:Company {name: 'AMD'}), (i:Industry {name: 'Semiconductor'}) MERGE (c)-[:OPERATES_IN]->(i)",
        
        # Company → Country
        "MATCH (c:Company {name: 'Nvidia'}), (co:Country {name: 'United States'}) MERGE (c)-[:LOCATED_IN]->(co)",
        "MATCH (c:Company {name: 'TSMC'}), (co:Country {name: 'Taiwan'}) MERGE (c)-[:LOCATED_IN]->(co)",
        "MATCH (c:Company {name: 'AMD'}), (co:Country {name: 'United States'}) MERGE (c)-[:LOCATED_IN]->(co)",
        "MATCH (c:Company {name: 'FPT Semiconductor'}), (co:Country {name: 'Vietnam'}) MERGE (c)-[:LOCATED_IN]->(co)",
        
        # Dependencies
        "MATCH (n:Company {name: 'Nvidia'}), (t:Company {name: 'TSMC'}) MERGE (n)-[:DEPENDS_ON {criticality: 'high'}]->(t)",
        "MATCH (a:Company {name: 'AMD'}), (t:Company {name: 'TSMC'}) MERGE (a)-[:DEPENDS_ON {criticality: 'high'}]->(t)",
        
        # Competition
        "MATCH (n:Company {name: 'Nvidia'}), (a:Company {name: 'AMD'}) MERGE (n)-[:COMPETES_WITH {segment: 'GPU'}]->(a)",
        "MATCH (a:Company {name: 'AMD'}), (n:Company {name: 'Nvidia'}) MERGE (a)-[:COMPETES_WITH {segment: 'GPU'}]->(n)",
        
        # Supply Chain - FPT Semiconductor supplies to major companies
        "MATCH (f:Company {name: 'FPT Semiconductor'}), (t:Company {name: 'TSMC'}) MERGE (f)-[:SUPPLIES {component: 'packaging'}]->(t)",
        "MATCH (f:Company {name: 'FPT Semiconductor'}), (n:Company {name: 'Nvidia'}) MERGE (f)-[:PARTNERS_WITH {type: 'testing'}]->(n)",
        
        # Macro → Industry
        "MATCH (m:MacroIndicator {name: 'Taiwan Strait Tension'}), (i:Industry {name: 'Semiconductor'}) MERGE (m)-[:IMPACTS {impact: 'negative', severity: 0.9}]->(i)",
        "MATCH (m:MacroIndicator {name: 'US-China Trade War'}), (i:Industry {name: 'Semiconductor'}) MERGE (m)-[:IMPACTS {impact: 'negative', severity: 0.7}]->(i)",
        
        # Macro → Country
        "MATCH (m:MacroIndicator {name: 'Taiwan Strait Tension'}), (c:Country {name: 'Taiwan'}) MERGE (m)-[:AFFECTS {severity: 0.95}]->(c)",
    ]
    
    for i, q in enumerate(queries, 1):
        run_query(driver, q)
        print(f"✅ {i}/{len(queries)}")
    
    # Test query
    print("\n🧪 Test: Nvidia risk paths")
    test = """
    MATCH path = (c:Company {name: 'Nvidia'})-[*1..2]-(related)
    RETURN [n IN nodes(path) | n.name] AS path
    LIMIT 10
    """
    results = run_query(driver, test)
    for r in results:
        print(f"  {r['path']}")
    
    driver.close()
    print("\n✅ Seed data complete!")

if __name__ == "__main__":
    main()
