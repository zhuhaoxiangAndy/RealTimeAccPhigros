"""Target ACC spec (consumed by v0.4 goal linkage)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Target:
    goal_acc: float = 0.95

    @classmethod
    def from_config(cls, cfg) -> "Target":
        return cls(goal_acc=cfg.goal_acc)

    def verdict(self, perfects: int, goods: int, total: int) -> bool:
        """True when the goal is already unreachable (red judgement)."""
        from acc import is_red

        return is_red(perfects, goods, total, self.goal_acc * 100.0)
