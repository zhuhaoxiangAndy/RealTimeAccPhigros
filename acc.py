"""Accuracy math per TECH_REQ ch.2 (never touch the formulas without doc sign-off)."""
from __future__ import annotations


def accuracy(perfects: int, goods: int, total: int, w_good: float = 0.65) -> float:
    """ACC = (P + 0.65*G) / N * 100."""
    if total <= 0:
        return 0.0
    return (perfects + w_good * goods) / total * 100.0


def max_reachable(perfects: int, goods: int, total: int, w_good: float = 0.65) -> float:
    """Best ACC if every remaining note is a Perfect."""
    remaining = max(0, total - perfects - goods)
    return accuracy(perfects + remaining, goods, total, w_good)


def is_red(perfects: int, goods: int, total: int, goal: float) -> bool:
    """Red judgement: max reachable ACC < goal ACC."""
    return max_reachable(perfects, goods, total) < goal
