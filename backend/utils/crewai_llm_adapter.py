from typing import Any, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.callbacks.manager import AsyncCallbackManagerForLLMRun
from anthropic import Anthropic
import os
from pydantic import PrivateAttr

class ChatAnthropic(BaseChatModel):
    """Anthropic chat model."""
    
    model: str = "claude-3-opus-20240229"
    temperature: float = 0.7
    api_key: str = os.getenv("ANTHROPIC_API_KEY")
    _client: Any = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_client', Anthropic(api_key=self.api_key))

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        message_content = "\n".join([m.content for m in messages])
        response = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=self.temperature,
            messages=[{"role": "user", "content": message_content}]
        )
        message = AIMessage(content=response.content[0].text)
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        message_content = "\n".join([m.content for m in messages])
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=self.temperature,
            messages=[{"role": "user", "content": message_content}]
        )
        message = AIMessage(content=response.content[0].text)
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        """Return type of chat model."""
        return "chat-anthropic"

class CrewAILLMAdapter:
    """Adapter to wrap ChatAnthropic for CrewAI Agents."""
    def __init__(self, model: str = "claude-3-opus-20240229", temperature: float = 0.7, **kwargs):
        # Initialize the underlying Anthropic Chat model
        self.llm = ChatAnthropic(model=model, temperature=temperature)

    @property
    def model(self) -> str:
        """Expose underlying LLM model name for compatibility with tests."""
        return getattr(self.llm, 'model', '')

    def generate(self, prompt: str, max_tokens: int = 512, **kwargs):
        """Synchronous generate method for CrewAI Agents."""
        result = self.llm._generate([{"role": "user", "content": prompt}], max_tokens=max_tokens, **kwargs)
        return result

    async def agenerate(self, prompts: list, max_tokens: int = 512, **kwargs):
        """Asynchronous generate method for CrewAI Agents."""
        result = await self.llm._agenerate([{"role": "user", "content": p} for p in prompts], max_tokens=max_tokens, **kwargs)
        return result
