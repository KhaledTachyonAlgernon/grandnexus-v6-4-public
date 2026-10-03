"""Execution profiles for safe, incremental GrandNexus activation."""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util


@dataclass(frozen=True)
class Profile:
    name: str
    optional_packages: tuple[str, ...] = ()

    def available(self) -> bool:
        return all(importlib.util.find_spec(package) is not None for package in self.optional_packages)

    def missing(self) -> list[str]:
        return [package for package in self.optional_packages if importlib.util.find_spec(package) is None]


PROFILES = {
    "light": Profile("light"),
    "api": Profile("api", ("fastapi", "uvicorn")),
    "ml": Profile("ml", ("torch", "sklearn", "sentence_transformers")),
    "robotics": Profile("robotics", ("gymnasium", "pybullet")),
    "full": Profile("full", ("torch", "sklearn", "sentence_transformers", "fastapi", "uvicorn")),
}


def get_profile(name: str = "light") -> Profile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"unknown profile: {name}") from exc
