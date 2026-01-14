"""
Cypher Translator
Converts extracted JSON entities and relationships into safe Cypher queries
Includes injection prevention and schema validation
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class CypherTranslator:
    """
    Translates extracted knowledge (entities and relationships) into Cypher queries
    Designed for Neo4j graph database with security best practices
    """
    
    def __init__(self, 
                 enable_timestamps: bool = True,
                 enable_deduplication: bool = True):
        """
        Initialize the Cypher translator
        
        Args:
            enable_timestamps: Add timestamps to nodes and relationships
            enable_deduplication: Use MERGE instead of CREATE to prevent duplicates
        """
        self.enable_timestamps = enable_timestamps
        self.enable_deduplication = enable_deduplication
        
        # Statistics
        self.stats = {
            "queries_generated": 0,
            "entities_translated": 0,
            "relationships_translated": 0,
            "sanitizations": 0
        }
    
    def sanitize_string(self, value: str) -> str:
        """
        Sanitize string to prevent Cypher injection
        
        Args:
            value: Raw string value
            
        Returns:
            Sanitized string safe for Cypher queries
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Remove or escape dangerous characters
        # Replace single quotes with escaped version
        value = value.replace("'", "\\'")
        
        # Remove newlines and control characters
        value = re.sub(r'[\n\r\t\x00-\x1f]', ' ', value)
        
        # Limit length to prevent memory issues
        max_length = 500
        if len(value) > max_length:
            value = value[:max_length]
            self.stats["sanitizations"] += 1
        
        # Remove trailing/leading whitespace
        value = value.strip()
        
        return value
    
    def sanitize_property_key(self, key: str) -> str:
        """
        Sanitize property key to be a valid Cypher identifier
        
        Args:
            key: Raw property key
            
        Returns:
            Valid Cypher property key
        """
        # Replace spaces and special characters with underscores
        key = re.sub(r'[^a-zA-Z0-9_]', '_', str(key))
        
        # Ensure it starts with a letter
        if key and not key[0].isalpha():
            key = 'prop_' + key
        
        # Lowercase for consistency
        key = key.lower()
        
        return key or 'unknown'
    
    def sanitize_label(self, label: str) -> str:
        """
        Sanitize label/type to be a valid Neo4j label
        
        Args:
            label: Raw label
            
        Returns:
            Valid Neo4j label
        """
        # Remove spaces and special characters
        label = re.sub(r'[^a-zA-Z0-9_]', '_', str(label))
        
        # Ensure it starts with a letter
        if label and not label[0].isalpha():
            label = 'Type_' + label
        
        # Uppercase for convention
        label = label.upper()
        
        return label or 'UNKNOWN'
    
    def translate_entity(self, entity: Dict[str, Any], metadata: Optional[Dict] = None) -> str:
        """
        Translate a single entity to a Cypher query
        
        Args:
            entity: Entity dictionary with 'name', 'type', 'properties'
            metadata: Optional metadata to add to the entity
            
        Returns:
            Cypher MERGE query string
        """
        name = self.sanitize_string(entity.get("name", ""))
        entity_type = self.sanitize_label(entity.get("type", "Entity"))
        
        if not name:
            return ""  # Skip empty entities
        
        # Build properties
        properties = entity.get("properties", {})
        if metadata:
            properties.update(metadata)
        
        # Add timestamps if enabled
        if self.enable_timestamps:
            properties["created_at"] = datetime.now().isoformat()
            properties["last_updated"] = datetime.now().isoformat()
        
        # Build properties string
        props_list = [f"name: '{name}'"]
        for key, value in properties.items():
            if key in ["name", "type"]:  # Skip reserved
                continue
            
            safe_key = self.sanitize_property_key(key)
            
            if isinstance(value, (int, float, bool)):
                props_list.append(f"{safe_key}: {value}")
            elif value is None:
                props_list.append(f"{safe_key}: null")
            else:
                safe_value = self.sanitize_string(str(value))
                props_list.append(f"{safe_key}: '{safe_value}'")
        
        props_str = ", ".join(props_list)
        
        # Use MERGE for deduplication or CREATE for performance
        if self.enable_deduplication:
            query = f"MERGE (n:{entity_type} {{name: '{name}'}}) SET n += {{{props_str}}}"
        else:
            query = f"CREATE (n:{entity_type} {{{props_str}}})"
        
        self.stats["entities_translated"] += 1
        return query
    
    def translate_relationship(self, relationship: Dict[str, Any], metadata: Optional[Dict] = None) -> str:
        """
        Translate a single relationship to a Cypher query
        
        Args:
            relationship: Relationship dict with 'source', 'target', 'type', 'properties'
            metadata: Optional metadata to add to the relationship
            
        Returns:
            Cypher MATCH + MERGE query string
        """
        source = self.sanitize_string(relationship.get("source", ""))
        target = self.sanitize_string(relationship.get("target", ""))
        rel_type = self.sanitize_label(relationship.get("type", "RELATED_TO"))
        
        if not source or not target:
            return ""  # Skip invalid relationships
        
        # Build properties
        properties = relationship.get("properties", {})
        if metadata:
            properties.update(metadata)
        
        # Add timestamps if enabled
        if self.enable_timestamps:
            properties["created_at"] = datetime.now().isoformat()
        
        # Build properties string
        props_list = []
        for key, value in properties.items():
            safe_key = self.sanitize_property_key(key)
            
            if isinstance(value, (int, float, bool)):
                props_list.append(f"{safe_key}: {value}")
            elif value is None:
                props_list.append(f"{safe_key}: null")
            else:
                safe_value = self.sanitize_string(str(value))
                props_list.append(f"{safe_key}: '{safe_value}'")
        
        props_str = ", ".join(props_list) if props_list else ""
        
        # Build query - MATCH both nodes first, then MERGE relationship
        if self.enable_deduplication:
            if props_str:
                query = f"""MATCH (a {{name: '{source}'}}), (b {{name: '{target}'}})
MERGE (a)-[r:{rel_type}]->(b)
ON CREATE SET r += {{{props_str}}}
ON MATCH SET r.last_seen = '{datetime.now().isoformat()}'"""
            else:
                query = f"""MATCH (a {{name: '{source}'}}), (b {{name: '{target}'}})
MERGE (a)-[r:{rel_type}]->(b)"""
        else:
            if props_str:
                query = f"""MATCH (a {{name: '{source}'}}), (b {{name: '{target}'}})
CREATE (a)-[r:{rel_type} {{{props_str}}}]->(b)"""
            else:
                query = f"""MATCH (a {{name: '{source}'}}), (b {{name: '{target}'}})
CREATE (a)-[r:{rel_type}]->(b)"""
        
        self.stats["relationships_translated"] += 1
        return query
    
    def translate_to_cypher(self, json_data: Dict[str, List[Dict]], metadata: Optional[Dict] = None) -> List[str]:
        """
        Translate extracted JSON to a list of Cypher queries
        
        Args:
            json_data: Dictionary with 'entities' and 'relationships' lists
            metadata: Optional metadata to add to all nodes/relationships
            
        Returns:
            List of Cypher query strings
        """
        queries = []
        
        # Translate entities first (must exist before relationships)
        entities = json_data.get("entities", [])
        for entity in entities:
            query = self.translate_entity(entity, metadata)
            if query:
                queries.append(query)
        
        # Then translate relationships
        relationships = json_data.get("relationships", [])
        for relationship in relationships:
            query = self.translate_relationship(relationship, metadata)
            if query:
                queries.append(query)
        
        self.stats["queries_generated"] += len(queries)
        return queries
    
    def translate_batch(self, json_data_list: List[Dict[str, List[Dict]]], metadata: Optional[Dict] = None) -> List[str]:
        """
        Translate multiple extraction results to Cypher queries
        
        Args:
            json_data_list: List of extraction results
            metadata: Optional metadata to add to all nodes/relationships
            
        Returns:
            Flat list of all Cypher queries
        """
        all_queries = []
        
        for json_data in json_data_list:
            queries = self.translate_to_cypher(json_data, metadata)
            all_queries.extend(queries)
        
        return all_queries
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get translation statistics
        
        Returns:
            Dictionary with statistics
        """
        return dict(self.stats)
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            "queries_generated": 0,
            "entities_translated": 0,
            "relationships_translated": 0,
            "sanitizations": 0
        }


# Test function
def test_translator():
    """Test the CypherTranslator with sample data"""
    translator = CypherTranslator()
    
    sample_data = {
        "entities": [
            {
                "name": "Samsung Electronics",
                "type": "COMPANY",
                "properties": {
                    "industry": "Technology",
                    "founded": 1969
                }
            },
            {
                "name": "Kim Jong-hee",
                "type": "PERSON",
                "properties": {
                    "role": "CEO"
                }
            },
            {
                "name": "Austin Facility",
                "type": "LOCATION",
                "properties": {
                    "state": "Texas",
                    "investment": "$10 billion"
                }
            }
        ],
        "relationships": [
            {
                "source": "Samsung Electronics",
                "target": "Kim Jong-hee",
                "type": "HAS_CEO",
                "properties": {
                    "since": 2020
                }
            },
            {
                "source": "Samsung Electronics",
                "target": "Austin Facility",
                "type": "OPERATES_IN",
                "properties": {
                    "investment_amount": 10000000000
                }
            }
        ]
    }
    
    print("Testing CypherTranslator...")
    print(f"Input: {len(sample_data['entities'])} entities, {len(sample_data['relationships'])} relationships\n")
    
    queries = translator.translate_to_cypher(sample_data, metadata={"source_file": "test.txt"})
    
    print(f"Generated {len(queries)} Cypher queries:\n")
    for i, query in enumerate(queries, 1):
        print(f"{i}. {query}\n")
    
    print(f"Statistics: {translator.get_stats()}")


if __name__ == "__main__":
    test_translator()
