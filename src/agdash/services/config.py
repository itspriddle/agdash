"""Configuration loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class AdGuardInstance:
    name: str
    url: str
    username: str
    password: str


@dataclass
class Config:
    adguard: list[AdGuardInstance] = field(default_factory=list)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> Config:
        if path is None:
            path = Path(__file__).parent.parent.parent.parent / "config" / "config.yaml"

        if not path.exists():
            print(f"Config not found: {path}")
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        instances = []
        for ag in data.get("adguard", []):
            instances.append(AdGuardInstance(
                name=ag.get("name", "AG"),
                url=ag.get("url", ""),
                username=ag.get("username", ""),
                password=ag.get("password", ""),
            ))

        return cls(adguard=instances)
