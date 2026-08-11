"""RealtimeAcc configuration: defaults plus TOML override (config.example.toml)."""
from __future__ import annotations
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class JudgeWeights:
    perfect: float = 1.0
    good: float = 0.65
    bad: float = 0.0
    miss: float = 0.0


@dataclass
class GameConfig:
    """All tunable settings; TOML file overrides defaults."""

    start: Optional[int] = None
    end: Optional[int] = None
    video_path: str = ""
    fps: int = 60

    # Score display region in the frame (x, y, w, h).
    score_region: tuple = (1910, 55, 450, 90)
    # Result detail page region (x, y, w, h); used by v0.2 reconciliation.
    result_region: tuple = (1150, 950, 700, 300)

    ocr_clip_limit: float = 2.0
    ocr_threshold: int = 100
    ocr_psm: int = 7
    ocr_whitelist: str = "0123456789"

    # Score-per-judgement prototype values observed on the reference chart.
    # The FIRST member of each family is the base value; ranges model the
    # per-frame floor drift of the games cumulative display.
    proto_p_base: int = 1227   # 900000 / N, floor drift observed as 1227/1228
    proto_p_chain: int = 1365  # 1000000 / N, floor drift observed as 1364/1365
    proto_g_base: int = 798    # 585000 / N
    proto_g_chain: int = 935

    weights: JudgeWeights = field(default_factory=JudgeWeights)
    goal_acc: float = 0.95  # v0.4 target; unused below

    sample_step: int = 12    # frame step while scanning offline video
    delta_cap: int = 22000   # max plausible score delta between samples

    def load(self, path: str | Path) -> "GameConfig":
        """Overlay values from a TOML file onto defaults."""
        p = Path(path)
        if not p.exists():
            return self
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
        box = raw.get("box", {})
        if "score" in box:
            self.score_region = tuple(box["score"][:4])
        if "result" in box:
            self.result_region = tuple(box["result"][:4])
        ocr = raw.get("ocr", {})
        for k in ("clip_limit", "threshold", "psm"):
            if k in ocr:
                setattr(self, "ocr_" + k, ocr[k])
        jw = raw.get("judge", {}).get("weights", {})
        for k in ("perfect", "good", "bad", "miss"):
            if k in jw:
                setattr(self.weights, k, jw[k])
        vid = raw.get("video", {})
        for k in ("start", "end"):
            if k in vid:
                setattr(self, k, vid[k])
        for k in ("video_path", "fps", "sample_step", "delta_cap", "goal_acc"):
            if k in vid:
                setattr(self, k, vid[k])
        return self
