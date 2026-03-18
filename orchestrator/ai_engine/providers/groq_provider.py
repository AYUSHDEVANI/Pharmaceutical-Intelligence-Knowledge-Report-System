"""
PIKRS AI Engine — Groq Provider (LangChain)
"""

import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from .base_provider import LLMProvider
from ..config import settings

logger = logging.getLogger("pikrs.ai_engine.groq")


class GroqProvider(LLMProvider):

    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY missing in environment")

        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            temperature=0.1,
            max_tokens=2048
        )

    async def generate(self, system_prompt: str, user_prompt: str) -> str:

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = await self.llm.ainvoke(messages)

        logger.debug("Groq raw response: %s", response.content)

        return response.content