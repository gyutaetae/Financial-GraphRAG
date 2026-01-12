"""
Memory Manager for 8GB RAM Optimization
Handles LLM context cleanup and memory monitoring
"""

import gc
import logging
from typing import Dict
import psutil

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    8GB RAM 환경을 위한 메모리 관리자
    
    역할:
    1. LLM 컨텍스트 정리 (노드 전환 시)
    2. 메모리 사용량 모니터링
    3. 임계값 초과 시 경고
    """
    
    def __init__(self, threshold_percent: float = 80.0):
        """
        Args:
            threshold_percent: 메모리 사용률 임계값 (기본 80%)
        """
        self.threshold_percent = threshold_percent
        self.cleanup_count = 0
    
    def flush_llm_memory(self, agent_name: str) -> Dict[str, float]:
        """
        LLM 컨텍스트 정리 및 가비지 컬렉션
        
        Args:
            agent_name: 현재 에이전트 이름
            
        Returns:
            메모리 사용량 정보 (정리 전후)
        """
        # 정리 전 메모리 상태
        before = self.get_memory_usage()
        
        # 가비지 컬렉션 실행
        gc.collect()
        
        # 정리 후 메모리 상태
        after = self.get_memory_usage()
        
        self.cleanup_count += 1
        
        freed_mb = before["used_gb"] * 1024 - after["used_gb"] * 1024
        
        logger.info(
            f"[MemoryManager] {agent_name} context flushed | "
            f"Freed: {freed_mb:.1f}MB | "
            f"Usage: {after['percent']:.1f}%"
        )
        
        return {
            "before_percent": before["percent"],
            "after_percent": after["percent"],
            "freed_mb": freed_mb
        }
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        현재 메모리 사용량 조회
        
        Returns:
            {
                "total_gb": 전체 메모리 (GB),
                "used_gb": 사용 중 메모리 (GB),
                "available_gb": 사용 가능 메모리 (GB),
                "percent": 사용률 (%)
            }
        """
        mem = psutil.virtual_memory()
        return {
            "total_gb": mem.total / (1024 ** 3),
            "used_gb": mem.used / (1024 ** 3),
            "available_gb": mem.available / (1024 ** 3),
            "percent": mem.percent
        }
    
    def check_memory_threshold(self) -> bool:
        """
        메모리 임계값 체크
        
        Returns:
            True if 임계값 초과, False otherwise
        """
        usage = self.get_memory_usage()
        
        if usage["percent"] > self.threshold_percent:
            logger.warning(
                f"[MemoryManager] Memory threshold exceeded! "
                f"Current: {usage['percent']:.1f}% > "
                f"Threshold: {self.threshold_percent}%"
            )
            return True
        
        return False
    
    def force_cleanup(self) -> None:
        """
        강제 메모리 정리 (임계값 초과 시)
        """
        logger.warning("[MemoryManager] Forcing aggressive memory cleanup...")
        
        # 여러 번 가비지 컬렉션 실행
        for _ in range(3):
            gc.collect()
        
        usage = self.get_memory_usage()
        logger.info(f"[MemoryManager] Force cleanup complete. Usage: {usage['percent']:.1f}%")
    
    def get_stats(self) -> Dict[str, any]:
        """
        메모리 관리 통계
        
        Returns:
            {
                "cleanup_count": 정리 실행 횟수,
                "current_usage": 현재 메모리 사용량,
                "threshold": 설정된 임계값
            }
        """
        return {
            "cleanup_count": self.cleanup_count,
            "current_usage": self.get_memory_usage(),
            "threshold_percent": self.threshold_percent
        }


# 전역 싱글톤 인스턴스
_memory_manager: MemoryManager = None


def get_memory_manager() -> MemoryManager:
    """
    전역 MemoryManager 인스턴스 반환
    
    Returns:
        MemoryManager 싱글톤 인스턴스
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(threshold_percent=80.0)
    return _memory_manager
