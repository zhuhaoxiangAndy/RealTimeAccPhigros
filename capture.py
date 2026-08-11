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


def live_frames(cfg: GameConfig, region: Optional[tuple] = None
                ) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_index, bgr_frame) from the primary monitor (live mode).

    `region` selects (left, top, width, height) of the monitor (defaults to
    the full monitor). Runs at the monitor refresh rate; the caller applies
    its own sampling cadence.
    """
    import mss
    import time

    with mss.mss() as sct:
        mon = region or sct.monitors[1]
        box = {"left": mon[0], "top": mon[1],
               "width": mon[2], "height": mon[3]}
        idx = 0
        while True:
            shot = sct.grab(box)
            arr = np.asarray(shot)[:, :, :3]
            yield idx, cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
            idx += 1
            time.sleep(0.01)
