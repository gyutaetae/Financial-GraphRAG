#!/usr/bin/env python3
"""
Complete Privacy Mode System Test
Tests the entire nano-graphrag replacement pipeline:
1. KnowledgeExtractor (Ollama → JSON)
2. CypherTranslator (JSON → Cypher)
3. Neo4jClient (Cypher → Neo4j)
4. PrivacyGraphBuilder (integrated pipeline)
5. PrivacyGraphRAGEngine (full system)
"""

import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_extractor():
    """Test 1: KnowledgeExtractor"""
    print("\n" + "=" * 60)
    print("Test 1: KnowledgeExtractor (Ollama → JSON)")
    print("=" * 60)
    
    from engine.extractor import KnowledgeExtractor
    
    extractor = KnowledgeExtractor()
    
    sample_text = """
    Samsung Electronics announced that CEO Kim Jong-hee will invest $10 billion
    in a new semiconductor factory in Austin, Texas. The company competes with
    Intel in the chip manufacturing market.
    """
    
    result = await extractor.extract_entities(sample_text)
    
    print(f"Entities: {len(result['entities'])}")
    for entity in result["entities"]:
        print(f"  - {entity['name']} ({entity['type']})")
    
    print(f"\nRelationships: {len(result['relationships'])}")
    for rel in result["relationships"]:
        print(f"  - {rel['source']} --[{rel['type']}]--> {rel['target']}")
    
    print(f"\nExtractor Stats: {extractor.get_stats()}")
    
    return result


def test_translator(extraction_result):
    """Test 2: CypherTranslator"""
    print("\n" + "=" * 60)
    print("Test 2: CypherTranslator (JSON → Cypher)")
    print("=" * 60)
    
    from engine.translator import CypherTranslator
    
    translator = CypherTranslator()
    
    metadata = {"source": "test.txt", "format": "txt"}
    queries = translator.translate_to_cypher(extraction_result, metadata)
    
    print(f"Generated {len(queries)} Cypher queries:")
    for i, query in enumerate(queries[:5], 1):  # Show first 5
        print(f"\n{i}. {query[:200]}...")
    
    print(f"\nTranslator Stats: {translator.get_stats()}")
    
    return queries


def test_neo4j_client():
    """Test 3: Neo4jClient"""
    print("\n" + "=" * 60)
    print("Test 3: Neo4jClient (Connection & Ping)")
    print("=" * 60)
    
    from db.neo4j_client import Neo4jClient
    from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
    
    if not NEO4J_URI or not NEO4J_PASSWORD:
        print("⚠️  Neo4j not configured. Skipping connection test.")
        return False
    
    client = Neo4jClient(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    
    # Test ping
    ping_result = client.ping()
    print(f"Status: {ping_result['status']}")
    print(f"Message: {ping_result['message']}")
    
    if ping_result["status"] == "ok":
        print(f"Details: {ping_result['details']}")
        client.close()
        return True
    else:
        print(f"Error: {ping_result['details'].get('suggestion', '')}")
        client.close()
        return False


async def test_privacy_graph_builder():
    """Test 4: PrivacyGraphBuilder (Integrated Pipeline)"""
    print("\n" + "=" * 60)
    print("Test 4: PrivacyGraphBuilder (Complete Pipeline)")
    print("=" * 60)
    
    from engine.privacy_graph_builder import PrivacyGraphBuilder
    from engine.privacy_ingestor import PrivacyIngestor
    import tempfile
    
    # Create test file
    test_content = """
    Apple Inc. announced record quarterly revenue of $90 billion in Q4 2023.
    CEO Tim Cook highlighted strong iPhone sales in emerging markets.
    The company competes with Samsung in the smartphone market.
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        ingestor = PrivacyIngestor()
        builder = PrivacyGraphBuilder()
        
        # Ingest file
        chunks = ingestor.ingest_file(test_file)
        
        # Build graph
        stats = await builder.build_graph_sequential(chunks)
        
        print(f"Build Stats:")
        print(f"  Chunks: {stats['chunks_processed']}")
        print(f"  Entities: {stats['entities_extracted']}")
        print(f"  Relationships: {stats['relationships_extracted']}")
        print(f"  Queries: {stats['queries_executed']}")
        print(f"  Errors: {stats['errors']}")
        
        return stats
        
    finally:
        os.unlink(test_file)


async def test_privacy_engine():
    """Test 5: PrivacyGraphRAGEngine (Full System)"""
    print("\n" + "=" * 60)
    print("Test 5: PrivacyGraphRAGEngine (Full System)")
    print("=" * 60)
    
    from engine.graphrag_engine import PrivacyGraphRAGEngine
    
    try:
        engine = PrivacyGraphRAGEngine()
        print("✅ Engine initialized successfully")
        
        # Test insert
        test_text = "Microsoft acquired OpenAI partnership for $10 billion in 2023."
        print(f"\nTesting ainsert with: {test_text[:50]}...")
        
        await engine.ainsert(test_text)
        print("✅ Insert completed")
        
        # Test query (if Neo4j available)
        print("\nTesting aquery...")
        try:
            response = await engine.aquery("What companies were mentioned?", mode="local")
            print(f"✅ Query response: {response[:200]}...")
        except Exception as e:
            print(f"⚠️  Query test skipped: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Privacy Mode Complete System Test")
    print("Testing nano-graphrag replacement")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Extractor
    try:
        extraction_result = await test_extractor()
        results["extractor"] = True
    except Exception as e:
        print(f"❌ Extractor test failed: {e}")
        results["extractor"] = False
        extraction_result = {"entities": [], "relationships": []}
    
    # Test 2: Translator
    try:
        queries = test_translator(extraction_result)
        results["translator"] = True
    except Exception as e:
        print(f"❌ Translator test failed: {e}")
        results["translator"] = False
    
    # Test 3: Neo4j Client
    try:
        results["neo4j_client"] = test_neo4j_client()
    except Exception as e:
        print(f"❌ Neo4j Client test failed: {e}")
        results["neo4j_client"] = False
    
    # Test 4: Privacy Graph Builder
    try:
        await test_privacy_graph_builder()
        results["graph_builder"] = True
    except Exception as e:
        print(f"❌ Graph Builder test failed: {e}")
        results["graph_builder"] = False
    
    # Test 5: Privacy Engine
    try:
        results["privacy_engine"] = await test_privacy_engine()
    except Exception as e:
        print(f"❌ Privacy Engine test failed: {e}")
        results["privacy_engine"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Privacy Mode system ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
