from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseChatModel


class LLMFactory:
    """
    Explicit LLM ownership.
    No shared models.
    No role ambiguity.
    """

    @staticmethod
    def atlas() -> BaseChatModel:
        return ChatOllama(
            model="llama3.1:latest",
            temperature=0,
            format="json",  
        )
    @staticmethod
    def atlasSummary() -> BaseChatModel:
        return ChatOllama(
            model="llama3.1:latest",
            temperature=0,
        )

    @staticmethod
    def nemesis() -> BaseChatModel:
        return ChatOllama(
            model="qwen2.5:7b",
            temperature=0,
        )

    @staticmethod
    def iris() -> BaseChatModel:
        return ChatOllama(
            model="phi3:latest",
            temperature=0,
        )
 