"""Judgement counting from the score display (offline video mode)."""
from __future__ import annotations

import re
from typing import Optional

import cv2
import numpy as np
import pytesseract

from config import GameConfig


def ocr_score(gray: np.ndarray, cfg: GameConfig) -> Optional[int]:
    """Read the 7-digit score value from a gray frame. Returns None on doubt.

    Pipeline (tuned on the reference capture):
      crop -> 2x cubic upscale -> CLAHE(2.0) -> binary(100) ->
      psm 7 digits-only OCR -> keep any valid 7-digit substring.
    """
    x, y, w, h = cfg.score_region
    crop_ = gray[y : y + h, x : x + w]
    if crop_.size == 0:
        return None
    crop_ = cv2.resize(crop_, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    crop_ = cv2.createCLAHE(clipLimit=cfg.ocr_clip_limit, tileGridSize=(8, 8)).apply(crop_)
    _, crop_ = cv2.threshold(crop_, cfg.ocr_threshold, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(
        crop_, config=f"--psm {cfg.ocr_psm} -c tessedit_char_whitelist={cfg.ocr_whitelist}"
    )
    digits = re.sub(r"[^0-9]", "", text)
    for i in range(len(digits) - 6):
        value = int(digits[i : i + 7])
        if 0 <= value < 1_000_000:
            return value
    return None


def decompose_delta(delta: int, cfg: GameConfig) -> Optional[tuple[int, int]]:
    """Split a score delta into (perfects, goods) note counts.

    A note family contributes an integer in [base, chain] per note
    (cumulative floor drift of the display). A delta is plausible if
    the interval [p*base_p + g*base_g, p*chain_p + g*chain_g] covers it.
    Perfects are rare->preferred (goods are ~5% of hits).
    """
    bases = (cfg.proto_p_base, cfg.proto_g_base)
    chains = (cfg.proto_p_chain, cfg.proto_g_chain)
    best = None
    for g in range(12):
        for p in range(15 - g):
            if p + g == 0:
                continue
            lo = p * bases[0] + g * bases[1]
            hi = p * chains[0] + g * chains[1]
            if lo <= delta <= hi:
                err = abs(2 * delta - (lo + hi)) / (p + g)
                cand = (p, g, err)
                if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] < best[1]):
                    best = cand
    return best


def _collect(frames, cfg: GameConfig, start, end):
    buf = []
    for idx, frame in frames:
        if start is not None and idx < start:
            continue
        if end is not None and idx >= end:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        score = ocr_score(gray, cfg)
        if score is not None:
            buf.append((idx, score))
    return buf


def anchor_window(buf, cfg: GameConfig) -> list:
    """Trim garbage pre/post reads via the backward walk from the last read.

    The settled final score is the last credible read. Walking backward stays
    inside the play window while each previous read is <= next + jitter and
    >= next - (delta_cap + jitter); menu/result garbage produces backward
    jumps that cut the window.
    """
    if not buf:
        return []
    hi = len(buf) - 1
    lo = hi
    jit = cfg.proto_g_base
    while lo > 0:
        prev_s, next_s = buf[lo - 1][1], buf[lo][1]
        if prev_s <= next_s + jit and prev_s >= next_s - cfg.delta_cap - jit:
            lo -= 1
        else:
            break
    return buf[lo : hi + 1]


class OfflineJudge:
    """Counts P/G/(B+M) by decomposing score deltas across the reel."""

    def __init__(self, cfg: GameConfig, start: Optional[int] = None,
                 end: Optional[int] = None):
        if start is None:
            start = cfg.start
        if end is None:
            end = cfg.end
        self.cfg = cfg
        self.start = start
        self.end = end
        self.perfects = 0
        self.goods = 0
        self.bad_miss = 0
        self.samples = 0
        self.skips = 0
        self.window = None

    def total(self) -> int:
        return self.perfects + self.goods + self.bad_miss

    def process_stream(self, frames) -> None:
        buf = _collect(frames, self.cfg, self.start, self.end)
        if self.start is None and self.end is None:
            buf = anchor_window(buf, self.cfg)
        self.window = buf
        prev: Optional[int] = None
        for _idx, score in self.window:
            self.samples += 1
            if prev is not None:
                delta = score - prev
                if delta <= 0:
                    self.skips += 1
                    continue
                if delta <= self.cfg.delta_cap:
                    hit = decompose_delta(delta, self.cfg)
                    if hit:
                        self.perfects += hit[0]
                        self.goods += hit[1]
                        prev = score
                        continue
                self.skips += 1
                continue
            prev = score