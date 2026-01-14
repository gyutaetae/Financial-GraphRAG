"""
Neo4j Client
Dedicated client for Neo4j operations with connection diagnostics and health checks
Implements lazy connection, ping functionality, and batch query execution
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import traceback

try:
    from neo4j import GraphDatabase, Driver, Session
    from neo4j.exceptions import ServiceUnavailable, AuthError, CypherSyntaxError
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("⚠️  neo4j package not installed. Install with: pip install neo4j")


class Neo4jClient:
    """
    Neo4j database client with diagnostics and connection management
    Designed for Privacy Mode with health checks and detailed error reporting
    """
    
    def __init__(self, 
                 uri: str,
                 user: str,
                 password: str,
                 database: str = "neo4j",
                 max_connection_lifetime: int = 3600,
                 max_connection_pool_size: int = 50,
                 connection_timeout: int = 30):
        """
        Initialize Neo4j client (lazy connection)
        
        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            user: Database username
            password: Database password
            database: Database name (default: neo4j)
            max_connection_lifetime: Max connection lifetime in seconds
            max_connection_pool_size: Max connections in pool
            connection_timeout: Connection timeout in seconds
        """
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j package is required. Install with: pip install neo4j")
        
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        
        self.connection_config = {
            "max_connection_lifetime": max_connection_lifetime,
            "max_connection_pool_size": max_connection_pool_size,
            "connection_timeout": connection_timeout,
            "encrypted": uri.startswith("neo4j+s://") or uri.startswith("bolt+s://")
        }
        
        self.driver: Optional[Driver] = None
        self._connected = False
        self._last_ping: Optional[datetime] = None
        
        # Statistics
        self.stats = {
            "queries_executed": 0,
            "queries_failed": 0,
            "total_execution_time": 0.0,
            "connections_made": 0,
            "ping_successes": 0,
            "ping_failures": 0
        }
    
    def _connect(self) -> Driver:
        """
        Establish connection to Neo4j (lazy initialization)
        
        Returns:
            Neo4j driver instance
        """
        if self.driver is None:
            try:
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    **self.connection_config
                )
                self._connected = True
                self.stats["connections_made"] += 1
                print(f"✅ Neo4j connection established: {self.uri}")
            except Exception as e:
                print(f"❌ Failed to create Neo4j driver: {e}")
                raise
        
        return self.driver
    
    def ping(self) -> Dict[str, Any]:
        """
        Test Neo4j connection and diagnose issues
        
        Returns:
            Diagnosis dictionary with status, message, and details
            Format: {
                "status": "ok" | "fail",
                "message": str,
                "details": {
                    "uri": str,
                    "user": str,
                    "database": str,
                    "error_type": str (if failed),
                    "suggestion": str (if failed)
                }
            }
        """
        details = {
            "uri": self.uri,
            "user": self.user,
            "database": self.database,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Attempt to connect and run simple query
            driver = self._connect()
            
            with driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                
                if record and record["test"] == 1:
                    self._last_ping = datetime.now()
                    self.stats["ping_successes"] += 1
                    
                    # Get database info
                    try:
                        db_info = session.run("CALL dbms.components() YIELD name, versions, edition")
                        component = db_info.single()
                        if component:
                            details["neo4j_version"] = component.get("versions", ["unknown"])[0]
                            details["edition"] = component.get("edition", "unknown")
                    except:
                        pass  # Ignore if can't get version info
                    
                    return {
                        "status": "ok",
                        "message": "Neo4j connection successful",
                        "details": details
                    }
        
        except AuthError as e:
            self.stats["ping_failures"] += 1
            details["error_type"] = "AuthError"
            details["error"] = str(e)
            details["suggestion"] = f"Check NEO4J_USERNAME ({self.user}) and NEO4J_PASSWORD in .env file"
            
            return {
                "status": "fail",
                "message": "Authentication failed",
                "details": details
            }
        
        except ServiceUnavailable as e:
            self.stats["ping_failures"] += 1
            details["error_type"] = "ServiceUnavailable"
            details["error"] = str(e)
            details["suggestion"] = f"Check if Neo4j is running at {self.uri}. Try: docker ps | grep neo4j"
            
            return {
                "status": "fail",
                "message": "Neo4j service unavailable",
                "details": details
            }
        
        except Exception as e:
            self.stats["ping_failures"] += 1
            details["error_type"] = type(e).__name__
            details["error"] = str(e)
            details["traceback"] = traceback.format_exc()
            details["suggestion"] = "Check NEO4J_URI format (should be bolt://host:port or neo4j://host:port)"
            
            return {
                "status": "fail",
                "message": f"Connection failed: {type(e).__name__}",
                "details": details
            }
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a single Cypher query synchronously
        
        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            
        Returns:
            Result dictionary with records and summary
        """
        start_time = datetime.now()
        
        try:
            driver = self._connect()
            
            with driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                records = [record.data() for record in result]
                summary = result.consume()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                self.stats["queries_executed"] += 1
                self.stats["total_execution_time"] += execution_time
                
                return {
                    "success": True,
                    "records": records,
                    "nodes_created": summary.counters.nodes_created,
                    "relationships_created": summary.counters.relationships_created,
                    "properties_set": summary.counters.properties_set,
                    "execution_time": execution_time
                }
        
        except CypherSyntaxError as e:
            self.stats["queries_failed"] += 1
            print(f"❌ Cypher syntax error: {e}")
            print(f"Query: {query[:200]}...")
            return {
                "success": False,
                "error": str(e),
                "error_type": "CypherSyntaxError",
                "query": query[:500]
            }
        
        except Exception as e:
            self.stats["queries_failed"] += 1
            print(f"❌ Query execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "query": query[:500]
            }
    
    async def execute_batch(self, queries: List[str], batch_size: int = 10, delay: float = 0.1) -> Dict[str, Any]:
        """
        Execute multiple Cypher queries in batches (memory optimized)
        
        Args:
            queries: List of Cypher query strings
            batch_size: Number of queries per batch
            delay: Delay between batches in seconds (to prevent overwhelming DB)
            
        Returns:
            Summary dictionary with results
        """
        results = {
            "total_queries": len(queries),
            "successful": 0,
            "failed": 0,
            "nodes_created": 0,
            "relationships_created": 0,
            "properties_set": 0,
            "execution_time": 0.0,
            "errors": []
        }
        
        start_time = datetime.now()
        
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            
            for query in batch:
                result = await asyncio.to_thread(self.execute_query, query)
                
                if result.get("success"):
                    results["successful"] += 1
                    results["nodes_created"] += result.get("nodes_created", 0)
                    results["relationships_created"] += result.get("relationships_created", 0)
                    results["properties_set"] += result.get("properties_set", 0)
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "query": query[:200],
                        "error": result.get("error", "Unknown error")
                    })
            
            # Delay between batches to prevent overwhelming the database
            if i + batch_size < len(queries):
                await asyncio.sleep(delay)
        
        results["execution_time"] = (datetime.now() - start_time).total_seconds()
        
        return results
    
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            try:
                self.driver.close()
                self._connected = False
                print("✅ Neo4j connection closed")
            except Exception as e:
                print(f"⚠️  Error closing Neo4j connection: {e}")
    
    def is_connected(self) -> bool:
        """Check if currently connected to Neo4j"""
        return self._connected and self.driver is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics
        
        Returns:
            Dictionary with statistics
        """
        stats = dict(self.stats)
        
        if stats["queries_executed"] > 0:
            stats["avg_execution_time"] = stats["total_execution_time"] / stats["queries_executed"]
            stats["success_rate"] = (
                stats["queries_executed"] / (stats["queries_executed"] + stats["queries_failed"]) * 100
            )
        else:
            stats["avg_execution_time"] = 0.0
            stats["success_rate"] = 0.0
        
        stats["last_ping"] = self._last_ping.isoformat() if self._last_ping else None
        
        return stats
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            "queries_executed": 0,
            "queries_failed": 0,
            "total_execution_time": 0.0,
            "connections_made": 0,
            "ping_successes": 0,
            "ping_failures": 0
        }
    
    def __enter__(self):
        """Context manager entry"""
        self._connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Test function
def test_neo4j_client():
    """Test the Neo4jClient with diagnostics"""
    import os
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    print(f"Testing Neo4jClient with {uri}...")
    
    client = Neo4jClient(uri, user, password)
    
    # Test ping
    print("\n1. Testing ping()...")
    ping_result = client.ping()
    print(f"Status: {ping_result['status']}")
    print(f"Message: {ping_result['message']}")
    print(f"Details: {ping_result['details']}")
    
    if ping_result["status"] == "ok":
        # Test simple query
        print("\n2. Testing query execution...")
        result = client.execute_query("MATCH (n) RETURN count(n) as node_count")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Node count: {result['records'][0]['node_count']}")
        
        # Test stats
        print("\n3. Statistics:")
        stats = client.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    client.close()


if __name__ == "__main__":
    test_neo4j_client()
