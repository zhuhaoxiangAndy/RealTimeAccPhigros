"""Frame sources: offline video (v0.2) and live screen (v0.3)."""
from __future__ import annotations
from typing import Iterator, Optional

import cv2
import numpy as np

from config import GameConfig


def frames_from_video(path: str, cfg: GameConfig) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_index, bgr_frame) for every cfg.sample_step-th frame.

    Sampling starts at cfg.start (aligned), so offline deltas match the
    reconciliation analysis; stops at cfg.end when set.
    """
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    end = cfg.end if cfg.end is not None else total
    idx = cfg.start if cfg.start is not None else 0
    try:
        while idx < end:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                break
            yield idx, frame
            idx += cfg.sample_step
    finally:
        cap.release()


def live_frames(cfg: GameConfig) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_index, bgr_frame) from the primary monitor (v0.3)."""
    raise NotImplementedError("live capture lands in v0.3")
