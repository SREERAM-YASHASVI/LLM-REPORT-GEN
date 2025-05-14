"""Ollama chat models."""
from typing import Any, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.callbacks.manager import AsyncCallbackManagerForLLMRun

class ChatOllama(BaseChatModel):
    """Simplified Ollama chat model."""
    
    model: str = "deepseek-r1:1.5b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        message = AIMessage(content="Hello! I'm a simplified Ollama chat model.")
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        message = AIMessage(content="Hello! I'm a simplified Ollama chat model.")
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        """Return type of chat model."""
        return "chat-ollama"
