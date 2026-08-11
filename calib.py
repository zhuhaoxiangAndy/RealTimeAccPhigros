"""Calibration helpers: locate UI regions inside a captured frame (v0.2+)."""
from __future__ import annotations

import cv2
import numpy as np


def crop(gray: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    return gray[y : y + h, x : x + w]


def find_result_page(gray: np.ndarray, region: tuple) -> bool:
    """Heuristic: the result detail page has a long static border band."""
    x, y, w, h = region
    band = gray[y + 150 : y + 300, x : x + w]
    return float(np.mean(band)) < 128
