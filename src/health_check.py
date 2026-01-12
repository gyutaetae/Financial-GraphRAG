"""
Health Check Module for Finance GraphRAG
하이브리드 클라우드 환경에서 서비스 연결 상태를 확인합니다.
"""

import os
import requests
from typing import Tuple, Dict
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class HealthChecker:
    """서비스 연결 상태 확인"""
    
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
    def check_neo4j(self) -> Tuple[bool, str]:
        """
        Neo4j 연결 확인 (로컬/Aura 모두 지원)
        
        Returns:
            (성공여부, 메시지)
        """
        try:
            from neo4j import GraphDatabase
            
            # URI 타입 감지
            if "neo4j+s://" in self.neo4j_uri or "neo4j+ssc://" in self.neo4j_uri:
                connection_type = "Neo4j Aura (Cloud)"
            elif "bolt://" in self.neo4j_uri:
                connection_type = "Neo4j Local"
            else:
                connection_type = "Neo4j (Unknown)"
            
            # 연결 시도
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            driver.verify_connectivity()
            driver.close()
            
            return True, f"✅ {connection_type} Connected"
            
        except Exception as e:
            error_msg = str(e)
            
            # 친절한 에러 메시지
            if "authentication" in error_msg.lower():
                return False, f"❌ Neo4j 인증 실패: 사용자명 또는 비밀번호를 확인하세요"
            elif "dns" in error_msg.lower():
                return False, f"❌ Neo4j 주소 오류: {self.neo4j_uri[:50]}... 를 확인하세요"
            elif "refused" in error_msg.lower():
                return False, f"❌ Neo4j 서버가 실행 중이 아닙니다 (포트: 7687)"
            else:
                return False, f"❌ Neo4j 연결 실패: {error_msg[:100]}"
    
    def check_ollama(self) -> Tuple[bool, str]:
        """
        Ollama LLM 서버 연결 확인 (로컬/Ngrok/클라우드)
        
        Returns:
            (성공여부, 메시지)
        """
        try:
            # 환경 감지
            if "localhost" in self.ollama_url or "127.0.0.1" in self.ollama_url:
                env_type = "Local"
            elif "ngrok" in self.ollama_url:
                env_type = "Ngrok Tunnel"
            elif "docker" in self.ollama_url or "ollama:" in self.ollama_url:
                env_type = "Docker"
            else:
                env_type = "Cloud"
            
            # /api/tags 엔드포인트로 모델 목록 확인
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_count = len(models)
                return True, f"✅ Ollama ({env_type}) - {model_count} models available"
            else:
                return False, f"❌ Ollama 응답 오류 (HTTP {response.status_code})"
                
        except requests.exceptions.Timeout:
            return False, f"❌ Ollama 타임아웃: {self.ollama_url} 가 응답하지 않습니다"
        except requests.exceptions.ConnectionError:
            return False, f"❌ Ollama 연결 실패: 서버가 실행 중인지 확인하세요"
        except Exception as e:
            return False, f"❌ Ollama 오류: {str(e)[:100]}"
    
    def check_backend(self) -> Tuple[bool, str]:
        """
        FastAPI 백엔드 서버 연결 확인
        
        Returns:
            (성공여부, 메시지)
        """
        try:
            response = requests.get(
                f"{self.api_url}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                engine_ready = data.get("engine_ready", False)
                
                if engine_ready:
                    return True, "✅ Backend API Connected"
                else:
                    return False, "⚠️ Backend 연결됨 (Engine 초기화 중)"
            else:
                return False, f"❌ Backend 응답 오류 (HTTP {response.status_code})"
                
        except requests.exceptions.ConnectionError:
            return False, f"❌ Backend 연결 실패: {self.api_url}"
        except Exception as e:
            return False, f"❌ Backend 오류: {str(e)[:100]}"
    
    def check_all(self) -> Dict[str, Tuple[bool, str]]:
        """
        모든 서비스 상태 확인
        
        Returns:
            {"neo4j": (bool, str), "ollama": (bool, str), "backend": (bool, str)}
        """
        return {
            "neo4j": self.check_neo4j(),
            "ollama": self.check_ollama(),
            "backend": self.check_backend()
        }
    
    def get_environment_info(self) -> Dict[str, str]:
        """
        현재 환경 정보 반환
        
        Returns:
            환경 정보 딕셔너리
        """
        return {
            "Neo4j URI": self.neo4j_uri,
            "Neo4j User": self.neo4j_user,
            "Ollama URL": self.ollama_url,
            "Backend URL": self.api_url,
            "Run Mode": os.getenv("RUN_MODE", "API"),
            "Environment": self._detect_environment()
        }
    
    def _detect_environment(self) -> str:
        """현재 실행 환경 감지"""
        if "STREAMLIT_SHARING" in os.environ:
            return "Streamlit Cloud"
        elif "DOCKER_CONTAINER" in os.environ or os.path.exists("/.dockerenv"):
            return "Docker"
        elif "neo4j+s://" in self.neo4j_uri:
            return "Hybrid (Local + Aura)"
        else:
            return "Local Development"


def quick_health_check() -> bool:
    """
    빠른 헬스 체크 (Neo4j만)
    
    Returns:
        Neo4j 연결 성공 여부
    """
    checker = HealthChecker()
    success, _ = checker.check_neo4j()
    return success


if __name__ == "__main__":
    """CLI로 헬스 체크 실행"""
    print("🏥 Finance GraphRAG Health Check")
    print("=" * 50)
    
    checker = HealthChecker()
    
    # 환경 정보
    print("\n📋 Environment Info:")
    env_info = checker.get_environment_info()
    for key, value in env_info.items():
        # 비밀번호는 마스킹
        if "password" in key.lower():
            value = "*" * len(value) if value else "(not set)"
        print(f"  {key}: {value}")
    
    # 서비스 체크
    print("\n🔍 Service Status:")
    results = checker.check_all()
    
    all_ok = True
    for service, (success, message) in results.items():
        print(f"  {message}")
        if not success:
            all_ok = False
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✅ All services are healthy!")
    else:
        print("⚠️ Some services need attention")
        print("\n💡 Troubleshooting:")
        print("  1. Check .env file configuration")
        print("  2. Ensure all services are running")
        print("  3. Verify network connectivity")
