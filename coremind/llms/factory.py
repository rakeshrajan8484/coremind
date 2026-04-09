# Previously this module used Ollama via langchain_ollama.ChatOllama.
# The original implementation is preserved below as comments for reference.
#
# from langchain_ollama import ChatOllama
# from langchain_core.language_models import BaseChatModel
#
# class LLMFactory:
#     """
#     Explicit LLM ownership.
#     No shared models.
#     No role ambiguity.
#     """
#
#     @staticmethod
#     def atlas() -> BaseChatModel:
#         return ChatOllama(
#             model="llama3.1:latest",
#             temperature=0,
#             format="json",  
#         )
#     @staticmethod
#     def atlasSummary() -> BaseChatModel:
#         return ChatOllama(
#             model="llama3.1:latest",
#             temperature=0,
#         )
#
#     @staticmethod
#     def nemesis() -> BaseChatModel:
#         return ChatOllama(
#             model="qwen2.5:7b",
#             temperature=0,
#         )
#
#     @staticmethod
#     def iris() -> BaseChatModel:
#         return ChatOllama(
#             model="phi3:latest",
#             temperature=0,
#         )

from openai import OpenAI
import os
from typing import List, Optional
from dotenv import load_dotenv

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from pydantic import Field

load_dotenv()


class HFRouterChatModel(BaseChatModel):
    model: str
    temperature: float = 0.0
    max_tokens: int = 512

    # 👇 declare client as a private field
    client: OpenAI = Field(default=None, exclude=True)

    def __init__(self, **data):
        super().__init__(**data)

        token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        # token ='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'
        if not token:
            raise ValueError("HUGGINGFACEHUB_API_TOKEN is not set")

        # 👇 now allowed
        object.__setattr__(
            self,
            "client",
            OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=token,
            ),
        )

    @property
    def _llm_type(self) -> str:
        return "hf_router"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> ChatResult:

        print("✅ USING HF ROUTER:", self.model)

        # Convert messages
        formatted_messages = []
        for m in messages:
            role = "user"
            if m.type == "ai":
                role = "assistant"
            elif m.type == "system":
                role = "system"

            formatted_messages.append({
                "role": role,
                "content": m.content
            })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        content = response.choices[0].message.content

        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content=content)
                )
            ]
        )


# -------------------------------------------------
# 🧠 LLM Factory
# -------------------------------------------------

class LLMFactory:

    @staticmethod
    def atlas() -> BaseChatModel:
        return HFRouterChatModel(
            model="meta-llama/Llama-3.1-70B-Instruct:scaleway",
            temperature=0.01,
            max_tokens=512,
        )

    @staticmethod
    def atlasSummary() -> BaseChatModel:
        return HFRouterChatModel(
            model="meta-llama/Llama-3.1-70B-Instruct:scaleway",
            temperature=0.01,
            max_tokens=512,
        )

    @staticmethod
    def nemesis() -> BaseChatModel:
        return HFRouterChatModel(
            model="meta-llama/Llama-3.1-70B-Instruct:scaleway",
            temperature=0.0,
            max_tokens=512,
        )

    @staticmethod
    def iris() -> BaseChatModel:
        return HFRouterChatModel(
            model="meta-llama/Llama-3.1-70B-Instruct:scaleway",
            temperature=0.01,
            max_tokens=512,
        )

    @staticmethod
    def argus() -> BaseChatModel:
        return HFRouterChatModel(
            model="meta-llama/Llama-3.1-70B-Instruct:scaleway",
            temperature=0.0,
            max_tokens=1024,
        )

    @staticmethod
    def nexis() -> BaseChatModel:
        return HFRouterChatModel(
            model="meta-llama/Llama-3.1-70B-Instruct:scaleway",
            temperature=0.0,
            max_tokens=2048,
        )