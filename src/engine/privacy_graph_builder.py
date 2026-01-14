"""
Privacy-First Custom Graph Builder
Refactored to use modular components:
- KnowledgeExtractor (Ollama → JSON)
- CypherTranslator (JSON → Cypher)
- Neo4jClient (Cypher → Neo4j)
"""

import gc
import time
from typing import Dict, List, Any, Generator, Optional
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    PRIVACY_BATCH_SIZE,
    PRIVACY_MAX_MEMORY_MB,
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD
)

# Import new modular components
from engine.extractor import KnowledgeExtractor
from engine.translator import CypherTranslator
from db.neo4j_client import Neo4jClient

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not installed. Memory monitoring disabled.")


class PrivacyGraphBuilder:
    """
    Privacy Mode graph builder using modular pipeline:
    1. KnowledgeExtractor: Text → Entities/Relationships (JSON)
    2. CypherTranslator: JSON → Cypher queries
    3. Neo4jClient: Execute queries → Neo4j database
    """
    
    def __init__(self, neo4j_db=None):
        """
        Initialize graph builder with new modular components
        
        Args:
            neo4j_db: Legacy Neo4jDatabase instance (optional, will use Neo4jClient instead)
        """
        # Initialize new modular components
        self.extractor = KnowledgeExtractor()
        self.translator = CypherTranslator(
            enable_timestamps=True,
            enable_deduplication=True
        )
        
        # Use Neo4jClient instead of legacy neo4j_db
        if NEO4J_URI and NEO4J_PASSWORD:
            self.neo4j_client = Neo4jClient(
                uri=NEO4J_URI,
                user=NEO4J_USERNAME,  # Neo4jClient uses 'user', not 'username'
                password=NEO4J_PASSWORD
            )
        else:
            self.neo4j_client = None
            print("⚠️  Neo4j not configured. Queries will not be executed.")
        
        self.batch_size = PRIVACY_BATCH_SIZE
        self.max_memory_mb = PRIVACY_MAX_MEMORY_MB
        
        # Statistics (combined from all components)
        self.stats = {
            "chunks_processed": 0,
            "entities_extracted": 0,
            "relationships_extracted": 0,
            "queries_executed": 0,
            "errors": 0
        }
    
    def check_memory_usage(self) -> Dict[str, float]:
        """
        Check current memory usage
        
        Returns:
            Dict with memory statistics
        """
        if not PSUTIL_AVAILABLE:
            return {"percent": 0, "used_mb": 0, "available_mb": 0}
        
        mem = psutil.virtual_memory()
        return {
            "percent": mem.percent,
            "used_mb": mem.used / (1024 * 1024),
            "available_mb": mem.available / (1024 * 1024)
        }
    
    def trigger_gc_if_needed(self) -> bool:
        """
        Trigger garbage collection if memory usage is high
        
        Returns:
            True if GC was triggered
        """
        mem_info = self.check_memory_usage()
        
        if mem_info["percent"] > 80:
            print(f"⚠️  High memory usage: {mem_info['percent']:.1f}%. Triggering GC...")
            gc.collect()
            time.sleep(0.5)  # Give system time to release memory
            
            new_mem = self.check_memory_usage()
            print(f"✅ Memory after GC: {new_mem['percent']:.1f}%")
            return True
        
        return False
    
    async def extract_graph_elements(self, text: str) -> Dict[str, Any]:
        """
        Extract entities and relationships using KnowledgeExtractor
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dict with entities and relationships in structured format
        """
        result = await self.extractor.extract_entities(text)
        
        # Update statistics
        self.stats["entities_extracted"] += len(result.get("entities", []))
        self.stats["relationships_extracted"] += len(result.get("relationships", []))
        
        return result
    
    def build_cypher_queries(self, graph_data: Dict[str, Any], metadata: Dict[str, Any]) -> List[str]:
        """
        Convert extracted graph elements to Cypher queries using CypherTranslator
        
        Args:
            graph_data: Dict with entities and relationships
            metadata: Source metadata for provenance
            
        Returns:
            List of Cypher query strings
        """
        queries = self.translator.translate_to_cypher(graph_data, metadata)
        return queries
    
    async def execute_queries(self, queries: List[str]) -> int:
        """
        Execute Cypher queries using Neo4jClient
        
        Args:
            queries: List of Cypher query strings
            
        Returns:
            Number of successfully executed queries
        """
        if not self.neo4j_client:
            print("⚠️  Neo4j not configured. Skipping query execution.")
            return 0
        
        # Use Neo4jClient's batch execution
        result = await self.neo4j_client.execute_batch(
            queries,
            batch_size=self.batch_size,
            delay=0.1
        )
        
        # Update statistics
        self.stats["queries_executed"] += result["successful"]
        self.stats["errors"] += result["failed"]
        
        if result["failed"] > 0:
            print(f"⚠️  {result['failed']} queries failed")
            for error in result["errors"][:3]:  # Show first 3 errors
                print(f"   Error: {error['error']}")
        
        return result["successful"]
    
    async def process_chunk(self, chunk: Dict[str, Any]) -> bool:
        """
        Process a single chunk: extract entities/relationships and build graph
        
        Args:
            chunk: Data chunk with text and metadata
            
        Returns:
            True if successful
        """
        try:
            # Check memory before processing
            self.trigger_gc_if_needed()
            
            # Extract graph elements
            text = chunk.get("text", "")
            metadata = chunk.get("metadata", {})
            
            if not text:
                return False
            
            print(f"🔍 Processing chunk {metadata.get('chunk_index', '?')} from {metadata.get('source', '?')}")
            
            graph_data = await self.extract_graph_elements(text)
            
            # Build Cypher queries
            queries = self.build_cypher_queries(graph_data, metadata)
            
            # Execute queries
            if queries:
                success = await self.execute_queries(queries)
                print(f"✅ Executed {success}/{len(queries)} queries")
            
            self.stats["chunks_processed"] += 1
            return True
            
        except Exception as e:
            print(f"⚠️  Chunk processing error: {e}")
            self.stats["errors"] += 1
            return False
    
    async def build_graph_sequential(self, chunks: Generator[Dict[str, Any], None, None]) -> Dict[str, Any]:
        """
        Build graph from chunks sequentially (memory-efficient)
        
        Args:
            chunks: Generator yielding data chunks
            
        Returns:
            Statistics dict
        """
        print("🚀 Starting sequential graph building...")
        start_time = time.time()
        
        batch = []
        
        for chunk in chunks:
            batch.append(chunk)
            
            # Process batch when full
            if len(batch) >= self.batch_size:
                for chunk_item in batch:
                    await self.process_chunk(chunk_item)
                
                # Clear batch and trigger GC
                batch = []
                gc.collect()
                
                # Show progress
                mem_info = self.check_memory_usage()
                print(f"📊 Progress: {self.stats['chunks_processed']} chunks | "
                      f"Memory: {mem_info['percent']:.1f}%")
        
        # Process remaining chunks
        if batch:
            for chunk_item in batch:
                await self.process_chunk(chunk_item)
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ Graph building completed in {elapsed:.1f}s")
        print(f"📊 Statistics:")
        print(f"   Chunks: {self.stats['chunks_processed']}")
        print(f"   Entities: {self.stats['entities_extracted']}")
        print(f"   Relationships: {self.stats['relationships_extracted']}")
        print(f"   Queries: {self.stats['queries_executed']}")
        print(f"   Errors: {self.stats['errors']}")
        
        return self.stats
    
    async def build_graph_from_file(self, filepath: str, ingestor) -> Dict[str, Any]:
        """
        Convenience method: ingest file and build graph in one go
        
        Args:
            filepath: Path to data file
            ingestor: PrivacyIngestor instance
            
        Returns:
            Statistics dict
        """
        chunks = ingestor.ingest_file(filepath)
        return await self.build_graph_sequential(chunks)


# Test function
async def test_graph_builder():
    """Test function for development"""
    import tempfile
    from engine.privacy_ingestor import PrivacyIngestor
    
    # Create test data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("""
Samsung Electronics is a major supplier to Apple Inc.
Samsung's CEO Kim Jong-hee announced a new semiconductor factory in Texas.
The company invested $10 billion in the Austin facility.
Samsung competes with Intel in the chip manufacturing market.
""")
        test_file = f.name
    
    # Initialize components
    ingestor = PrivacyIngestor(chunk_size=500)
    builder = PrivacyGraphBuilder(neo4j_db=None)  # No DB for testing
    
    # Test extraction only
    print("\n=== Testing Entity/Relationship Extraction ===")
    chunks = list(ingestor.ingest_file(test_file))
    
    for chunk in chunks[:1]:  # Test first chunk only
        graph_data = await builder.extract_graph_elements(chunk["text"])
        
        print(f"\n📊 Extracted Data:")
        print(f"Entities: {len(graph_data.get('entities', []))}")
        for entity in graph_data.get("entities", []):
            print(f"  - {entity['name']} ({entity['type']})")
        
        print(f"\nRelationships: {len(graph_data.get('relationships', []))}")
        for rel in graph_data.get("relationships", []):
            print(f"  - {rel['source']} --[{rel['type']}]--> {rel['target']}")
        
        # Test Cypher generation
        queries = builder.build_cypher_queries(graph_data, chunk["metadata"])
        print(f"\n📝 Generated {len(queries)} Cypher queries")
        for i, query in enumerate(queries[:3], 1):
            print(f"\nQuery {i}:")
            print(query)
    
    # Cleanup
    import os
    os.unlink(test_file)
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_graph_builder())
