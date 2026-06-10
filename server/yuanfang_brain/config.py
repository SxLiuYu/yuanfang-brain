"""Configuration management for yuanfang-brain."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


def _load_secret(path_str: str) -> str:
    """Read a secret from a base64 file. Empty string if path empty or file missing."""
    if not path_str:
        return ""
    p = Path(os.path.expanduser(path_str))
    if not p.exists():
        return ""
    try:
        return base64.b64decode(p.read_bytes()).decode().strip()
    except Exception:
        return ""


class HAConfig(BaseModel):
    url: str = "http://192.168.1.10:8123"
    token: str = ""
    token_file: str = ""  # path to base64 file; takes precedence over `token`

    def resolved_token(self) -> str:
        return _load_secret(self.token_file) or self.token


class MiniMaxConfig(BaseModel):
    api_key: str = ""
    api_key_file: str = ""
    base: str = "https://api.minimaxi.com/v1"  # Coding Plan (sk-cp) OpenAI-compatible
    tts_model: str = "speech-01"
    asr_model: str = "whisper-1"
    llm_model: str = "M2.7"
    # group_id: kept optional for legacy callers; Coding Plan doesn't need it
    group_id: str = ""

    def resolved_key(self) -> str:
        # Priority: env var > b64 file > yaml literal
        env_key = os.environ.get("MINIMAX_CN_API_KEY", "").strip()
        if env_key:
            return env_key
        file_key = _load_secret(self.api_key_file)
        if file_key:
            return file_key
        return self.api_key

    def resolved_group_id(self) -> str:
        # Read group_id from ~/.hermes/.secrets/minimax_cn_group_id.b64 if present
        secrets_dir = Path(os.path.expanduser("~/.hermes/.secrets"))
        group_id_file = secrets_dir / "minimax_cn_group_id.b64"
        if group_id_file.exists():
            try:
                gid = base64.b64decode(group_id_file.read_bytes()).decode().strip()
                if gid:
                    return gid
            except Exception:
                pass
        # Fall back to yaml literal
        return self.group_id


class Config(BaseModel):
    server_host: str = "0.0.0.0"
    server_port: int = 7100  # avoid macOS Control Center on 7000
    ws_port: int = 7101
    ha: HAConfig = Field(default_factory=HAConfig)
    minimax: MiniMaxConfig = Field(default_factory=MiniMaxConfig)
    whisper_model: str = "tiny"
    log_level: str = "INFO"

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        if path is None:
            path = Path(os.path.expanduser("~/.yuanfang-brain/config.yaml"))
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
            return cls.model_validate(data)
        return cls()


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config

