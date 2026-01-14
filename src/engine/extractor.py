"""
Knowledge Extractor
Ollama-based entity and relationship extraction from business documents
Optimized for 8GB RAM with 500-character chunk processing
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from ollama import AsyncClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️  ollama not installed. Install with: pip install ollama")

from config import OLLAMA_BASE_URL, LOCAL_MODELS


class KnowledgeExtractor:
    """
    Extract structured knowledge (entities and relationships) from text using Ollama LLM
    Designed for financial and business document analysis
    """
    
    def __init__(self, 
                 model: str = None,
                 base_url: str = None,
                 max_retries: int = 3,
                 timeout: int = 60):
        """
        Initialize the knowledge extractor
        
        Args:
            model: Ollama model name (default: from config)
            base_url: Ollama server URL (default: from config)
            max_retries: Maximum retry attempts for failed requests
            timeout: Request timeout in seconds
        """
        self.model = model or LOCAL_MODELS.get("llm", "qwen2.5-coder:3b")
        self.base_url = base_url or OLLAMA_BASE_URL
        self.max_retries = max_retries
        self.timeout = timeout
        
        if not OLLAMA_AVAILABLE:
            raise ImportError("ollama package is required. Install with: pip install ollama")
        
        self.client = AsyncClient(host=self.base_url)
        
        # Statistics
        self.stats = {
            "extractions": 0,
            "entities_found": 0,
            "relationships_found": 0,
            "errors": 0,
            "retries": 0
        }
    
    def _build_extraction_prompt(self, text: str) -> str:
        """
        Build the prompt for entity/relationship extraction
        
        Args:
            text: Input text to analyze
            
        Returns:
            Formatted prompt string
        """
        return f"""Extract business entities and their relationships from the following text.
Return ONLY valid JSON format with no additional text or explanation.

Required JSON format:
{{
  "entities": [
    {{"name": "EntityName", "type": "COMPANY|PERSON|PRODUCT|LOCATION|FINANCIAL_METRIC", "properties": {{"key": "value"}}}}
  ],
  "relationships": [
    {{"source": "EntityA", "target": "EntityB", "type": "RELATIONSHIP_TYPE", "properties": {{"key": "value"}}}}
  ]
}}

Entity Types:
- COMPANY: Business organizations
- PERSON: Individuals (CEOs, executives, employees)
- PRODUCT: Products or services
- LOCATION: Geographic locations
- FINANCIAL_METRIC: Revenue, profit, market cap, etc.

Common Relationship Types:
- SUPPLIES, PURCHASES, COMPETES_WITH (business operations)
- HAS_CEO, EMPLOYS, LOST_EMPLOYEE, HIRED (personnel)
- HAS_DEBT, OWNS_ASSET, INVESTS_IN (financial)
- LOCATED_IN, OPERATES_IN (geographic)
- PRODUCES, MANUFACTURES (production)

Text to analyze (max 500 characters):
{text[:500]}

JSON output:"""
    
    async def extract_entities(self, text: str) -> Dict[str, List[Dict]]:
        """
        Extract entities and relationships from text using Ollama LLM
        
        Args:
            text: Input text (automatically truncated to 500 chars for RAM optimization)
            
        Returns:
            Dictionary with 'entities' and 'relationships' lists
            Format: {
                "entities": [{"name": str, "type": str, "properties": dict}],
                "relationships": [{"source": str, "target": str, "type": str, "properties": dict}]
            }
        """
        if not text or not text.strip():
            return {"entities": [], "relationships": []}
        
        # Truncate to 500 chars for 8GB RAM optimization
        text = text[:500]
        
        prompt = self._build_extraction_prompt(text)
        
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self.client.chat(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a business analyst that extracts structured data. Always respond with valid JSON only."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        options={
                            "temperature": 0.1,  # Low temperature for consistent extraction
                            "num_predict": 1000,  # Limit response length
                        }
                    ),
                    timeout=self.timeout
                )
                
                # Extract content from response
                content = response.get("message", {}).get("content", "")
                
                # Parse JSON
                result = self._parse_json_response(content)
                
                # Update statistics
                self.stats["extractions"] += 1
                self.stats["entities_found"] += len(result.get("entities", []))
                self.stats["relationships_found"] += len(result.get("relationships", []))
                
                return result
                
            except asyncio.TimeoutError:
                self.stats["retries"] += 1
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"⏱️  Timeout. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    self.stats["errors"] += 1
                    print(f"❌ Extraction failed after {self.max_retries} attempts (timeout)")
                    return {"entities": [], "relationships": []}
            
            except Exception as e:
                self.stats["retries"] += 1
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️  Error: {type(e).__name__}: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    self.stats["errors"] += 1
                    print(f"❌ Extraction failed after {self.max_retries} attempts: {e}")
                    return {"entities": [], "relationships": []}
        
        return {"entities": [], "relationships": []}
    
    def _parse_json_response(self, content: str) -> Dict[str, List[Dict]]:
        """
        Parse JSON from LLM response, handling common formatting issues
        
        Args:
            content: Raw LLM response content
            
        Returns:
            Parsed dictionary with entities and relationships
        """
        # Remove markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            data = json.loads(content)
            
            # Validate structure
            if not isinstance(data, dict):
                print("⚠️  Response is not a dictionary")
                return {"entities": [], "relationships": []}
            
            entities = data.get("entities", [])
            relationships = data.get("relationships", [])
            
            # Validate entities
            valid_entities = []
            for entity in entities:
                if isinstance(entity, dict) and "name" in entity and "type" in entity:
                    # Ensure properties exist
                    if "properties" not in entity:
                        entity["properties"] = {}
                    valid_entities.append(entity)
            
            # Validate relationships
            valid_relationships = []
            for rel in relationships:
                if isinstance(rel, dict) and "source" in rel and "target" in rel and "type" in rel:
                    # Ensure properties exist
                    if "properties" not in rel:
                        rel["properties"] = {}
                    valid_relationships.append(rel)
            
            return {
                "entities": valid_entities,
                "relationships": valid_relationships
            }
        
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing error: {e}")
            print(f"Content preview: {content[:200]}...")
            return {"entities": [], "relationships": []}
    
    async def extract_batch(self, texts: List[str]) -> List[Dict[str, List[Dict]]]:
        """
        Extract entities from multiple text chunks in parallel (with concurrency limit)
        
        Args:
            texts: List of text strings to process
            
        Returns:
            List of extraction results
        """
        # Process in batches to avoid overwhelming Ollama server
        max_concurrent = 3  # Conservative limit for 8GB RAM
        results = []
        
        for i in range(0, len(texts), max_concurrent):
            batch = texts[i:i + max_concurrent]
            tasks = [self.extract_entities(text) for text in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"⚠️  Batch extraction error: {result}")
                    results.append({"entities": [], "relationships": []})
                else:
                    results.append(result)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get extraction statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            **self.stats,
            "success_rate": (
                (self.stats["extractions"] / (self.stats["extractions"] + self.stats["errors"]) * 100)
                if (self.stats["extractions"] + self.stats["errors"]) > 0
                else 0
            )
        }
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            "extractions": 0,
            "entities_found": 0,
            "relationships_found": 0,
            "errors": 0,
            "retries": 0
        }


# Test function
async def test_extractor():
    """Test the KnowledgeExtractor with sample text"""
    extractor = KnowledgeExtractor()
    
    sample_text = """
    Samsung Electronics announced that CEO Kim Jong-hee will lead a new 
    semiconductor factory investment in Texas. The company invested $10 billion 
    in the Austin facility. Samsung competes with Intel in the chip manufacturing market.
    """
    
    print("Testing KnowledgeExtractor...")
    print(f"Model: {extractor.model}")
    print(f"Base URL: {extractor.base_url}")
    print(f"\nInput text: {sample_text[:100]}...\n")
    
    result = await extractor.extract_entities(sample_text)
    
    print("Extraction Results:")
    print(f"Entities: {len(result['entities'])}")
    for entity in result["entities"]:
        print(f"  - {entity['name']} ({entity['type']})")
    
    print(f"\nRelationships: {len(result['relationships'])}")
    for rel in result["relationships"]:
        print(f"  - {rel['source']} --[{rel['type']}]--> {rel['target']}")
    
    print(f"\nStatistics: {extractor.get_stats()}")


if __name__ == "__main__":
    asyncio.run(test_extractor())
