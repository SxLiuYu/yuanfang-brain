"""Configuration management for yuanfang-brain."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class HAConfig(BaseModel):
    url: str = "http://192.168.1.10:8123"
    token: str = ""


class MiniMaxConfig(BaseModel):
    api_key: str = ""
    group_id: str = ""


class Config(BaseModel):
    server_host: str = "0.0.0.0"
    server_port: int = 7000
    ws_port: int = 7001
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
