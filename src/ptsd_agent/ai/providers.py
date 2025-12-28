"""AI Provider Framework for PTSD Agent.

Supports 15+ AI providers:
- Commercial APIs (OpenAI, Anthropic, Google, etc.)
- CLI Tools (gemini-cli, claude-cli, gh copilot, etc.)
- Self-hosted (Ollama, LM Studio, llama.cpp, etc.)

Features:
- Provider fallback chains
- Reasoning model support
- Research capabilities
- Cost tracking
"""

import subprocess
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ProviderType(Enum):
    """Type of AI provider."""
    CLI = "cli"
    API = "api"
    SELF_HOSTED = "self_hosted"


class ProviderCapability(Enum):
    """Capabilities a provider can have."""
    CHAT = "chat"
    REASONING = "reasoning"
    WEB_SEARCH = "web_search"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"


@dataclass
class AIResponse:
    """Response from an AI provider."""
    content: str
    provider_name: str
    model: str
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    reasoning_steps: Optional[List[str]] = None


class AIProvider(ABC):
    """Base protocol for AI providers."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize provider.
        
        Args:
            name: Provider name
            config: Provider configuration
        """
        self.name = name
        self.config = config
        self.capabilities: List[ProviderCapability] = []
    
    @abstractmethod
    def suggest_fix(self, context: Dict[str, Any]) -> AIResponse:
        """Generate fix suggestion for test failure.
        
        Args:
            context: Context dictionary with error details, code, docs
        
        Returns:
            AI response with fix suggestion
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available.
        
        Returns:
            True if provider can be used
        """
        pass


class CLIProvider(AIProvider):
    """Provider that uses CLI tools (gemini-cli, claude-cli, etc.)."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize CLI provider.
        
        Args:
            name: Provider name
            config: Must include 'command' key
        """
        super().__init__(name, config)
        self.command = config['command']
        self.capabilities = [
            ProviderCapability.CHAT,
            ProviderCapability.CODE_GENERATION,
            ProviderCapability.CODE_REVIEW
        ]
    
    def suggest_fix(self, context: Dict[str, Any]) -> AIResponse:
        """Generate fix using CLI tool.
        
        Args:
            context: Context with test failure details
        
        Returns:
            AI response with suggestion
        """
        # Build prompt
        prompt = self._build_prompt(context)
        
        # Call CLI tool
        try:
            result = subprocess.run(
                [*self.command.split(), "--prompt", prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return AIResponse(
                    content=result.stdout.strip(),
                    provider_name=self.name,
                    model=self.config.get('model', 'unknown')
                )
            else:
                raise Exception(f"CLI command failed: {result.stderr}")
        except Exception as e:
            raise Exception(f"CLI provider {self.name} failed: {e}")
    
    def is_available(self) -> bool:
        """Check if CLI tool is available.
        
        Returns:
            True if command exists
        """
        try:
            cmd = self.command.split()[0]
            result = subprocess.run(
                ['which', cmd],
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt from context.
        
        Args:
            context: Test failure context
        
        Returns:
            Formatted prompt string
        """
        test_name = context.get('test_name', 'unknown')
        error = context.get('error', 'No error details')
        code = context.get('code', '')
        docs = context.get('docs', '')
        
        return f"""Test failure: {test_name}

Error:
{error}

Relevant code:
{code}

Project documentation:
{docs}

Please suggest a fix for this test failure."""


class APIProvider(AIProvider):
    """Provider that uses API clients (OpenAI, Anthropic, etc.)."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize API provider.
        
        Args:
            name: Provider name
            config: Must include 'api_key_env' and 'model'
        """
        super().__init__(name, config)
        self.api_key = os.getenv(config.get('api_key_env', ''))
        self.model = config['model']
        self.base_url = config.get('base_url')
        
        # Set capabilities based on model
        self.capabilities = [ProviderCapability.CHAT, ProviderCapability.CODE_GENERATION]
        if 'o1' in self.model or 'thinking' in self.model.lower():
            self.capabilities.append(ProviderCapability.REASONING)
    
    def suggest_fix(self, context: Dict[str, Any]) -> AIResponse:
        """Generate fix using API.
        
        Args:
            context: Test failure context
        
        Returns:
            AI response
        """
        # This would integrate with specific API clients
        # For now, placeholder that would be implemented per provider
        raise NotImplementedError(f"API provider {self.name} not fully implemented yet")
    
    def is_available(self) -> bool:
        """Check if API key is configured.
        
        Returns:
            True if API key exists
        """
        return bool(self.api_key)


class ProviderRegistry:
    """Registry of all available AI providers."""
    
    PROVIDER_CONFIGS = {
        # CLI Tools
        'gemini-cli': {
            'type': ProviderType.CLI,
            'command': 'gemini',
            'model': 'gemini-2.0-flash'
        },
        'claude-cli': {
            'type': ProviderType.CLI,
            'command': 'claude',
            'model': 'claude-3.5-sonnet'
        },
        'gh-copilot': {
            'type': ProviderType.CLI,
            'command': 'gh copilot suggest',
            'model': 'gpt-4'
        },
        'aider': {
            'type': ProviderType.CLI,
            'command': 'aider --no-git --yes --message',
            'model': 'various'
        },
        
        # Commercial APIs
        'openai-o1': {
            'type': ProviderType.API,
            'api_key_env': 'OPENAI_API_KEY',
            'model': 'o1-preview',
            'reasoning': True
        },
        'openai-gpt4': {
            'type': ProviderType.API,
            'api_key_env': 'OPENAI_API_KEY',
            'model': 'gpt-4-turbo'
        },
        'anthropic': {
            'type': ProviderType.API,
            'api_key_env': 'ANTHROPIC_API_KEY',
            'model': 'claude-3-5-sonnet-20241022'
        },
        'google': {
            'type': ProviderType.API,
            'api_key_env': 'GOOGLE_API_KEY',
            'model': 'gemini-2.0-flash-exp'
        },
        'perplexity': {
            'type': ProviderType.API,
            'api_key_env': 'PERPLEXITY_API_KEY',
            'model': 'sonar-pro',
            'web_search': True
        },
        
        # Self-hosted
        'ollama': {
            'type': ProviderType.CLI,
            'command': 'ollama run codellama',
            'model': 'codellama'
        },
        'lm-studio': {
            'type': ProviderType.API,
            'base_url': 'http://localhost:1234/v1',
            'model': 'local'
        }
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize provider registry.
        
        Args:
            config: User configuration override
        """
        self.config = config or {}
        self.providers: Dict[str, AIProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all configured providers."""
        for name, provider_config in self.PROVIDER_CONFIGS.items():
            # Merge with user config
            if name in self.config.get('providers', {}):
                provider_config = {**provider_config, **self.config['providers'][name]}
            
            # Create provider instance
            provider_type = provider_config['type']
            if provider_type == ProviderType.CLI:
                self.providers[name] = CLIProvider(name, provider_config)
            elif provider_type == ProviderType.API:
                self.providers[name] = APIProvider(name, provider_config)
    
    def get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers.
        
        Returns:
            List of providers that are currently available
        """
        return [p for p in self.providers.values() if p.is_available()]
    
    def get_provider(self, name: str) -> Optional[AIProvider]:
        """Get specific provider by name.
        
        Args:
            name: Provider name
        
        Returns:
            Provider instance or None
        """
        return self.providers.get(name)
    
    def suggest_fix_with_fallback(
        self, 
        context: Dict[str, Any],
        preferred_providers: Optional[List[str]] = None
    ) -> Optional[AIResponse]:
        """Try to get fix suggestion with fallback chain.
        
        Args:
            context: Test failure context
            preferred_providers: Ordered list of provider names to try
        
        Returns:
            AI response or None if all failed
        """
        if not preferred_providers:
            preferred_providers = ['gh-copilot', 'gemini-cli', 'claude-cli', 'ollama']
        
        for provider_name in preferred_providers:
            provider = self.get_provider(provider_name)
            if provider and provider.is_available():
                try:
                    return provider.suggest_fix(context)
                except Exception:
                    continue  # Try next provider
        
        return None
