"""Target ACC spec (consumed by v0.4 goal linkage)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Target:
    goal_acc: float = 0.95

    @classmethod
    def from_config(cls, cfg) -> "Target":
        return cls(goal_acc=cfg.goal_acc)
