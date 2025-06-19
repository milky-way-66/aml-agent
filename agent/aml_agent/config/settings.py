import os
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import SettingsConfigDict, BaseSettings
import json

class AppSettings(BaseSettings):
    """Application settings using Pydantic for environment variable management."""
    
    # Storage settings
    storage_dir: str = Field(
        default_factory=lambda: os.path.join(os.path.expanduser("~"), ".aml_agent", "data")
    )
    
    # RAG API settings
    rag_api_base_url: Optional[str] = Field(None, env="RAG_API_BASE_URL")
    rag_api_key: Optional[str] = Field(None, env="RAG_API_KEY")
    
    # MCP API settings
    mcp_api_base_url: Optional[str] = Field(None, env="MCP_API_BASE_URL")
    mcp_api_key: Optional[str] = Field(None, env="MCP_API_KEY")
    
    # Anthropic API settings
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    # UI settings
    ui_theme: str = "dark"
    ui_verbose: bool = True
    
    # Configure environment variable loading
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        keys = key.split(".")
        
        # Handle first level directly from model fields
        if len(keys) == 1:
            return getattr(self, keys[0], default)
        
        # Handle nested values based on our structure
        if keys[0] == "rag_api":
            if keys[1] == "base_url":
                return self.rag_api_base_url or default
            elif keys[1] == "api_key":
                return self.rag_api_key or default
        elif keys[0] == "mcp_api":
            if keys[1] == "base_url":
                return self.mcp_api_base_url or default
            elif keys[1] == "api_key":
                return self.mcp_api_key or default
        elif keys[0] == "anthropic" and keys[1] == "api_key":
            return self.anthropic_api_key or default
        elif keys[0] == "ui":
            if keys[1] == "theme":
                return self.ui_theme or default
            elif keys[1] == "verbose":
                return self.ui_verbose or default
        
        return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to a dictionary format."""
        return {
            "storage_dir": self.storage_dir,
            "rag_api": {
                "base_url": self.rag_api_base_url,
                "api_key": self.rag_api_key
            },
            "mcp_api": {
                "base_url": self.mcp_api_base_url,
                "api_key": self.mcp_api_key
            },
            "anthropic": {
                "api_key": self.anthropic_api_key
            },
            "ui": {
                "theme": self.ui_theme,
                "verbose": self.ui_verbose
            }
        }

# Create a global settings instance
settings = AppSettings()
