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

import os
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.language_models import BaseChatModel


class LLMFactory:
    """
    Explicit LLM ownership.
    Replaced Ollama with HuggingFaceHub using Mistral-7B for all roles.
    """

    @staticmethod
    def _mistral_model(temperature: float = 0.01) -> BaseChatModel:
        # 1. Initialize the Endpoint (The connection to the model)
        # Note: temperature must be > 0.0 for many HF models; 0.01 is effectively greedy.
        llm = HuggingFaceEndpoint(
            repo_id = "meta-llama/Llama-3.2-3B-Instruct" ,
            huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
            temperature=temperature,
            max_new_tokens=512,
            timeout=300
        )

        # 2. Wrap in ChatHuggingFace to return a BaseChatModel (System/Human/AI messages)
        return ChatHuggingFace(llm=llm)

    @staticmethod
    def atlas() -> BaseChatModel:
        return LLMFactory._mistral_model(temperature=0.01)

    @staticmethod
    def atlasSummary() -> BaseChatModel:
        return LLMFactory._mistral_model(temperature=0.01)

    @staticmethod
    def nemesis() -> BaseChatModel:
        return LLMFactory._mistral_model(temperature=0.01)

    @staticmethod
    def iris() -> BaseChatModel:
        return LLMFactory._mistral_model(temperature=0.01)
 