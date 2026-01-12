"""
모든 에이전트의 공통 기능을 제공하는 베이스 클래스
"""

import os
import psutil
from abc import ABC, abstractmethod
from typing import Optional
from openai import AsyncOpenAI

from .agent_context import AgentContext
from config import OPENAI_API_KEY, OPENAI_BASE_URL


class BaseAgent(ABC):
    """
    모든 에이전트의 베이스 클래스
    공통 기능: LLM 호출, 메모리 체크, 로깅
    """
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        temperature: float = 0.2,
        max_retries: int = 3,
        memory_threshold: float = 85.0
    ):
        """
        Args:
            name: 에이전트 이름
            system_prompt: 시스템 프롬프트
            temperature: LLM 온도 (0.0 = 정확, 2.0 = 창의적)
            max_retries: LLM 호출 실패 시 재시도 횟수
            memory_threshold: 메모리 사용률 임계값 (%)
        """
        self.name = name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_retries = max_retries
        self.memory_threshold = memory_threshold
        
        # OpenAI 클라이언트 초기화 (메모리 효율적)
        self.llm_client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL if OPENAI_BASE_URL else None
        )
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentContext:
        """
        에이전트의 핵심 로직 실행
        서브클래스에서 반드시 구현해야 함
        
        Args:
            context: 공유 컨텍스트
            
        Returns:
            업데이트된 컨텍스트
        """
        pass
    
    async def _call_llm(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 2000
    ) -> str:
        """
        OpenAI API 호출 (재시도 로직 포함)
        
        Args:
            prompt: 사용자 프롬프트
            temperature: 온도 (None이면 기본값 사용)
            max_tokens: 최대 토큰 수
            
        Returns:
            LLM 응답 텍스트
        """
        temp = temperature if temperature is not None else self.temperature
        
        for attempt in range(self.max_retries):
            try:
                self._check_memory()
                
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temp,
                    max_tokens=max_tokens
                )
                
                return response.choices[0].message.content.strip()
                
            except MemoryError as e:
                self._log(f"메모리 부족: {e}")
                raise
            except Exception as e:
                self._log(f"LLM 호출 실패 (시도 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
        
        raise RuntimeError(f"{self.name}: LLM 호출 최대 재시도 초과")
    
    def _check_memory(self) -> None:
        """
        메모리 사용률 체크 (8GB RAM 환경 대응)
        임계값 초과 시 MemoryError 발생
        """
        mem = psutil.virtual_memory()
        if mem.percent > self.memory_threshold:
            raise MemoryError(
                f"{self.name}: 메모리 사용률 {mem.percent:.1f}% 초과 "
                f"(임계값: {self.memory_threshold}%)"
            )
    
    def _log(self, message: str) -> None:
        """로깅 (에이전트 이름 포함)"""
        print(f"[{self.name}] {message}")
    
    def get_memory_usage(self) -> dict:
        """현재 메모리 사용률 반환 (모니터링용)"""
        mem = psutil.virtual_memory()
        return {
            "total_gb": mem.total / (1024 ** 3),
            "used_gb": mem.used / (1024 ** 3),
            "available_gb": mem.available / (1024 ** 3),
            "percent": mem.percent
        }
