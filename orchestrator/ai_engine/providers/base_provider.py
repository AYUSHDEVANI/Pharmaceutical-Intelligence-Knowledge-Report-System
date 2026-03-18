"""
PIKRS AI Engine — Provider Abstraction
======================================
Protocol definition ensuring all LLM providers (Groq, OpenAI, etc.)
adhere to the same API contract for the AI Generator.
"""

from typing import Protocol

class LLMProvider(Protocol):
    """
    Interface for dynamic LLM generation providers.
    """
    
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Takes the system and user instructions, sends to the external
        LLM provider, and returns the raw string response (expected to be JSON).
        
        Args:
            system_prompt (str): High-level system instructions.
            user_prompt (str): Formatted user data payload.
            
        Returns:
            str: Raw generated string (JSON output) from the LLM.
        """
        ...
