"""
LLM Configuration - Supports both OpenAI and Ollama
Allows switching between production (OpenAI) and development (Ollama)
"""

import os
from typing import Literal

LLMProvider = Literal["openai", "ollama"]


class LLMConfig:
    """LLM provider configuration"""
    
    @staticmethod
    def get_provider() -> LLMProvider:
        """Determine which LLM provider to use"""
        use_local = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
        return "ollama" if use_local else "openai"
    
    @staticmethod
    def get_ollama_config() -> dict:
        """Get Ollama configuration"""
        return {
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        }
    
    @staticmethod
    def get_openai_config() -> dict:
        """Get OpenAI configuration"""
        return {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-4o-mini"
        }
    
    @staticmethod
    def print_config() -> None:
        """Print current LLM configuration"""
        provider = LLMConfig.get_provider()
        print(f"\n🤖 LLM Provider: {provider.upper()}")
        
        if provider == "ollama":
            config = LLMConfig.get_ollama_config()
            print(f"   Base URL: {config['base_url']}")
            print(f"   Model: {config['model']}")
            print(f"   💡 Make sure Ollama is running: 'ollama serve'")
        else:
            config = LLMConfig.get_openai_config()
            print(f"   Model: {config['model']}")
            print(f"   API Key: {'✅ Set' if config['api_key'] else '❌ Not set'}")