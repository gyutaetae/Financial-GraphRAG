"""
MCP Manager - MCP 서버 생명주기 관리
"""

import asyncio
import json
import os
import subprocess
import time
from typing import Dict, Any, Optional, List
from pathlib import Path


class MCPManager:
    """
    MCP 서버 관리자
    
    역할:
    1. MCP 서버 프로세스 시작/종료
    2. Lazy loading (필요할 때만 시작)
    3. 자동 정리 (미사용 서버 종료)
    4. 메모리 최적화
    """
    
    def __init__(self, config_path: str = "mcp-config.json"):
        """
        Args:
            config_path: MCP 설정 파일 경로
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.servers: Dict[str, subprocess.Popen] = {}
        self.clients: Dict[str, Any] = {}
        self.last_used: Dict[str, float] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # 설정 로드
        self.settings = self.config.get("settings", {})
        self.lazy_load = self.settings.get("lazyLoadDefault", True)
        self.auto_cleanup_minutes = self.settings.get("autoCleanupMinutes", 5)
        self.max_concurrent = self.settings.get("maxConcurrentServers", 2)
        
        print(f"✅ MCP Manager 초기화 (lazy_load={self.lazy_load})")
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            print(f"⚠️  MCP 설정 파일이 없습니다: {self.config_path}")
            return {"mcpServers": {}, "settings": {}}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"❌ MCP 설정 파일 로드 실패: {e}")
            return {"mcpServers": {}, "settings": {}}
    
    async def get_tool(self, server_name: str, tool_name: str) -> Optional[Any]:
        """
        MCP 도구 가져오기 (lazy loading)
        
        Args:
            server_name: 서버 이름 (예: "yahoo-finance")
            tool_name: 도구 이름 (예: "get_stock_price")
            
        Returns:
            도구 함수 또는 None
        """
        # 서버가 실행 중이 아니면 시작
        if server_name not in self.servers:
            success = await self._start_server(server_name)
            if not success:
                return None
        
        # 마지막 사용 시간 업데이트
        self.last_used[server_name] = time.time()
        
        # 클라이언트에서 도구 가져오기
        client = self.clients.get(server_name)
        if client:
            return client.get(tool_name)
        
        return None
    
    async def _start_server(self, server_name: str) -> bool:
        """
        MCP 서버 시작
        
        Args:
            server_name: 서버 이름
            
        Returns:
            성공 여부
        """
        server_config = self.config.get("mcpServers", {}).get(server_name)
        if not server_config:
            print(f"❌ 서버 설정을 찾을 수 없습니다: {server_name}")
            return False
        
        if not server_config.get("enabled", True):
            print(f"⚠️  서버가 비활성화되어 있습니다: {server_name}")
            return False
        
        # 동시 실행 서버 수 제한
        if len(self.servers) >= self.max_concurrent:
            await self._cleanup_least_used()
        
        try:
            print(f"🚀 MCP 서버 시작 중: {server_name}")
            
            # 환경 변수 준비
            env = os.environ.copy()
            server_env = server_config.get("env", {})
            for key, value in server_env.items():
                # ${VAR} 형식 치환
                if value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    env_value = os.getenv(env_var, "")
                    if not env_value:
                        print(f"⚠️  환경 변수가 설정되지 않았습니다: {env_var}")
                    env[key] = env_value
                else:
                    env[key] = value
            
            # 프로세스 시작 (실제로는 stdio 통신이 필요하지만 여기서는 mock)
            # 실제 구현에서는 mcp 패키지의 StdioServerParameters를 사용
            command = server_config.get("command", "npx")
            args = server_config.get("args", [])
            
            # 여기서는 실제 프로세스를 시작하지 않고 mock 클라이언트 생성
            # 실제 구현에서는 mcp.client.stdio.stdio_client를 사용
            self.servers[server_name] = None  # Mock
            self.clients[server_name] = self._create_mock_client(server_name, server_config)
            self.last_used[server_name] = time.time()
            
            print(f"✅ MCP 서버 시작 완료: {server_name}")
            return True
            
        except Exception as e:
            print(f"❌ MCP 서버 시작 실패: {server_name}, {e}")
            return False
    
    def _create_mock_client(self, server_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock 클라이언트 생성 (실제 구현에서는 MCP 클라이언트 사용)
        
        Args:
            server_name: 서버 이름
            config: 서버 설정
            
        Returns:
            도구 딕셔너리
        """
        tools = {}
        for tool_name in config.get("tools", []):
            tools[tool_name] = self._create_mock_tool(server_name, tool_name)
        return tools
    
    def _create_mock_tool(self, server_name: str, tool_name: str):
        """Mock 도구 함수 생성"""
        async def mock_tool(**kwargs):
            print(f"🔧 Mock MCP 호출: {server_name}.{tool_name}({kwargs})")
            
            # Yahoo Finance mock
            if server_name == "yahoo-finance":
                if tool_name == "get_stock_price":
                    return {
                        "ticker": kwargs.get("ticker", "UNKNOWN"),
                        "price": 450.25,
                        "change": 5.75,
                        "change_percent": 1.29,
                        "volume": 12500000,
                        "timestamp": "2026-01-12T10:30:00Z"
                    }
                elif tool_name == "get_company_info":
                    return {
                        "ticker": kwargs.get("ticker", "UNKNOWN"),
                        "name": "Example Corp",
                        "sector": "Technology",
                        "industry": "Semiconductors",
                        "description": "A leading technology company"
                    }
            
            # Tavily Search mock
            elif server_name == "tavily-search":
                if tool_name == "tavily_search":
                    return {
                        "results": [
                            {
                                "title": "Example News Article",
                                "url": "https://example.com/news",
                                "content": "Latest news about the query",
                                "score": 0.95
                            }
                        ]
                    }
            
            return {"error": "Not implemented"}
        
        return mock_tool
    
    async def _cleanup_least_used(self):
        """가장 오래 사용되지 않은 서버 종료"""
        if not self.servers:
            return
        
        # 가장 오래된 서버 찾기
        oldest_server = min(self.last_used.items(), key=lambda x: x[1])
        server_name = oldest_server[0]
        
        await self._stop_server(server_name)
    
    async def _stop_server(self, server_name: str):
        """
        MCP 서버 종료
        
        Args:
            server_name: 서버 이름
        """
        if server_name in self.servers:
            print(f"🛑 MCP 서버 종료: {server_name}")
            
            process = self.servers[server_name]
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception as e:
                    print(f"⚠️  서버 종료 중 오류: {e}")
            
            del self.servers[server_name]
            if server_name in self.clients:
                del self.clients[server_name]
            if server_name in self.last_used:
                del self.last_used[server_name]
    
    async def start_cleanup_task(self):
        """자동 정리 태스크 시작"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._auto_cleanup_loop())
    
    async def _auto_cleanup_loop(self):
        """미사용 서버 자동 정리 루프"""
        while True:
            try:
                await asyncio.sleep(60)  # 1분마다 체크
                
                current_time = time.time()
                timeout_seconds = self.auto_cleanup_minutes * 60
                
                servers_to_stop = []
                for server_name, last_used_time in self.last_used.items():
                    if current_time - last_used_time > timeout_seconds:
                        servers_to_stop.append(server_name)
                
                for server_name in servers_to_stop:
                    print(f"🧹 미사용 서버 자동 정리: {server_name}")
                    await self._stop_server(server_name)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️  자동 정리 중 오류: {e}")
    
    async def shutdown(self):
        """모든 서버 종료"""
        print("🛑 MCP Manager 종료 중...")
        
        # 자동 정리 태스크 취소
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 모든 서버 종료
        server_names = list(self.servers.keys())
        for server_name in server_names:
            await self._stop_server(server_name)
        
        print("✅ MCP Manager 종료 완료")
    
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 조회"""
        return {
            "running_servers": list(self.servers.keys()),
            "server_count": len(self.servers),
            "max_concurrent": self.max_concurrent,
            "lazy_load": self.lazy_load,
            "auto_cleanup_minutes": self.auto_cleanup_minutes
        }
