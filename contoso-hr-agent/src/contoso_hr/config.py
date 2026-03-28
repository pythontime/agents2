"""
Configuration management for Contoso HR Agent.

All settings loaded from environment variables (via .env file).
Azure AI Foundry is the exclusive LLM/embeddings backend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment variables.

    Attributes:
        azure_foundry_endpoint: Azure AI Foundry endpoint URL.
        azure_foundry_key: API key for Azure AI Foundry.
        azure_foundry_chat_model: Deployment name for chat completion.
        azure_foundry_embedding_model: Deployment name for embeddings.
        azure_foundry_api_version: Azure OpenAI API version string.
        brave_api_key: Brave Search API key (optional, for web search tool).
        llm_temperature: LLM temperature (0.0 deterministic, 1.0 creative).
        watch_poll_seconds: Seconds between resume watcher polls.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        engine_port: FastAPI server port.
        mcp_port: FastMCP server port.
        project_root: Root directory of this project.
    """

    # Azure AI Foundry — chat
    azure_foundry_endpoint: str
    azure_foundry_key: str
    azure_foundry_chat_model: str
    azure_foundry_api_version: str = "2024-05-01-preview"

    # Azure AI Foundry — embeddings
    azure_foundry_embedding_model: str = "text-embedding-3-large"

    # Optional integrations
    brave_api_key: Optional[str] = None

    # Azure subscription context (informational; used by Azure MCP server)
    azure_tenant_id: Optional[str] = None
    azure_subscription_id: Optional[str] = None
    azure_resource_group: Optional[str] = None

    # Runtime
    llm_temperature: float = 0.2
    watch_poll_seconds: int = 3
    log_level: str = "INFO"
    engine_port: int = 8080
    mcp_port: int = 8081

    # Directories (derived from project_root in __post_init__)
    project_root: Path = field(default_factory=Path.cwd)
    incoming_dir: Path = field(init=False)
    processed_dir: Path = field(init=False)
    knowledge_dir: Path = field(init=False)
    chroma_dir: Path = field(init=False)
    data_dir: Path = field(init=False)
    outgoing_dir: Path = field(init=False)

    def __post_init__(self):
        data = self.project_root / "data"
        self.incoming_dir = data / "incoming"
        self.processed_dir = data / "processed"
        self.knowledge_dir = data / "knowledge"
        self.chroma_dir = data / "chroma"
        self.data_dir = data
        self.outgoing_dir = data / "outgoing"

    @classmethod
    def from_env(cls, project_root: Optional[Path] = None) -> "Config":
        """Load configuration from .env file and environment variables.

        Args:
            project_root: Project root directory. Auto-detected if None.

        Returns:
            Populated Config instance.

        Raises:
            ValueError: If required Azure credentials are missing.
        """
        if project_root is None:
            project_root = _find_project_root()

        # Load .env from project root — always override so the file wins over
        # any stale shell exports from previous sessions.
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
        else:
            # Fallback: try CWD (useful when running scripts from subdirectories)
            cwd_env = Path.cwd() / ".env"
            if cwd_env.exists():
                load_dotenv(cwd_env, override=True)

        endpoint = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", "")
        key = os.getenv("AZURE_AI_FOUNDRY_KEY", "")
        chat_model = os.getenv("AZURE_AI_FOUNDRY_CHAT_MODEL", "gpt-4o")
        embedding_model = os.getenv(
            "AZURE_AI_FOUNDRY_EMBEDDING_MODEL", "text-embedding-3-large"
        )
        api_version = os.getenv("AZURE_AI_FOUNDRY_API_VERSION", "2024-05-01-preview")

        return cls(
            azure_foundry_endpoint=endpoint,
            azure_foundry_key=key,
            azure_foundry_chat_model=chat_model,
            azure_foundry_embedding_model=embedding_model,
            azure_foundry_api_version=api_version,
            brave_api_key=os.getenv("BRAVE_API_KEY"),
            azure_tenant_id=os.getenv("AZURE_TENANT_ID"),
            azure_subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
            azure_resource_group=os.getenv("AZURE_RESOURCE_GROUP"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            watch_poll_seconds=int(os.getenv("WATCH_POLL_SECONDS", "3")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            engine_port=int(os.getenv("ENGINE_PORT", "8080")),
            mcp_port=int(os.getenv("MCP_PORT", "8081")),
            project_root=project_root,
        )

    def get_llm(self):
        """Return AzureChatOpenAI instance for LangChain nodes.

        Returns:
            langchain_openai.AzureChatOpenAI configured for Azure AI Foundry.
        """
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_endpoint=self.azure_foundry_endpoint,
            api_key=self.azure_foundry_key,
            azure_deployment=self.azure_foundry_chat_model,
            api_version=self.azure_foundry_api_version,
            temperature=self.llm_temperature,
        )

    def get_crew_llm(self):
        """Return CrewAI LLM wrapper pointing at Azure AI Foundry.

        CrewAI uses LiteLLM under the hood with provider prefixes.

        Returns:
            crewai.LLM configured for Azure AI Foundry.
        """
        from crewai import LLM

        return LLM(
            model=f"azure/{self.azure_foundry_chat_model}",
            temperature=self.llm_temperature,
            api_key=self.azure_foundry_key,
            base_url=self.azure_foundry_endpoint,
            api_version=self.azure_foundry_api_version,
        )

    def get_embeddings(self):
        """Return AzureOpenAIEmbeddings for ChromaDB vectorization.

        Returns:
            langchain_openai.AzureOpenAIEmbeddings configured for Foundry.
        """
        from langchain_openai import AzureOpenAIEmbeddings

        return AzureOpenAIEmbeddings(
            azure_endpoint=self.azure_foundry_endpoint,
            api_key=self.azure_foundry_key,
            azure_deployment=self.azure_foundry_embedding_model,
            api_version=self.azure_foundry_api_version,
        )

    def validate(self) -> list[str]:
        """Validate required configuration.

        Returns:
            List of validation error strings (empty = valid).
        """
        errors: list[str] = []
        if not self.azure_foundry_endpoint:
            errors.append("AZURE_AI_FOUNDRY_ENDPOINT is not set")
        if not self.azure_foundry_key:
            errors.append("AZURE_AI_FOUNDRY_KEY is not set")
        if not self.azure_foundry_chat_model:
            errors.append("AZURE_AI_FOUNDRY_CHAT_MODEL is not set")
        return errors


def _find_project_root() -> Path:
    """Walk up from the current file to find the project root (pyproject.toml)."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


# Global lazy-loaded config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Return the global Config instance (lazy-loaded from environment)."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config() -> None:
    """Reset the global config (useful for testing)."""
    global _config
    _config = None
