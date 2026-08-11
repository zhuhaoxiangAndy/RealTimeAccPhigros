"""Basic pytest coverage: ACC math, delta decomposition, window anchoring.

TECH_REQ ch.10: judgement logic must have basic pytest coverage.
"""
import pytest

from acc import accuracy, is_red, max_reachable
from config import GameConfig
from judge import anchor_window, decompose_delta


def cfg():
    return GameConfig()


def test_acc_math():
    assert accuracy(693, 35, 733) == pytest.approx((693 + 0.65 * 35) / 733 * 100)
    assert accuracy(0, 0, 0) == 0.0


def test_max_reachable():
    assert max_reachable(0, 0, 10) == 100.0
    assert max_reachable(693, 35, 733) == accuracy(698, 35, 733)


def test_is_red():
    assert not is_red(10, 0, 100, 99.0)
    assert not is_red(0, 0, 100, 99.0)
    assert is_red(0, 50, 100, 90.0)
    assert not is_red(0, 50, 100, 70.0)


@pytest.mark.parametrize(
    "delta,expect",
    [
        (1227, (1, 0)),
        (1228, (1, 0)),
        (1364, (1, 0)),
        (1365, (1, 0)),
        (798, (0, 1)),
        (935, (0, 1)),
        (2455, (2, 0)),
        (2729, (2, 0)),
        (4093, (3, 0)),
        (2026, (1, 1)),
        (2454, (2, 0)),
        (2394, (0, 3)),
    ],
)
def test_decompose_delta(delta, expect):
    hit = decompose_delta(delta, cfg())
    assert hit is not None
    assert hit[0] == expect[0] and hit[1] == expect[1]


def test_decompose_rejects_junk():
    assert decompose_delta(7, cfg()) is None
    assert decompose_delta(50000, cfg()) is None


def test_anchor_window_trim():
    buf = [(0, 900000), (1, 900000), (2, 100), (3, 910880)]
    win = anchor_window(buf, cfg())
    assert win == [(3, 910880)]


def test_anchor_window_clean():
    buf = [(0, 100), (1, 200), (2, 300)]
    assert anchor_window(buf, cfg()) == buf