"""RealtimeAcc CLI:
    python main.py video <path> [--config config.example.toml]
    python main.py raw   <path>   (print raw score reads; debugging)
    python main.py run            (live mode; v0.3)
"""
from __future__ import annotations

import argparse
import sys

import capture
import judge
from config import GameConfig


def cmd_video(args) -> int:
    cfg = GameConfig().load(args.config)
    cfg.video_path = args.path
    if args.start is not None:
        cfg.start = args.start
    if args.end is not None:
        cfg.end = args.end
    j = judge.OfflineJudge(cfg)
    j.process_stream(capture.frames_from_video(args.path, cfg))
    print("perfects:", j.perfects)
    print("goods:   ", j.goods)
    print("bad+miss:", j.bad_miss)
    print("total:   ", j.total())
    return 0


def cmd_raw(args) -> int:
    cfg = GameConfig().load(args.config)
    import cv2

    for idx, frame in capture.frames_from_video(args.path, cfg):
        score = judge.ocr_score(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cfg)
        print(idx, score)
    return 0


def cmd_run(args) -> int:
    print("live mode arrives in v0.3")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="realtimeacc")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_video = sub.add_parser("video")
    p_video.add_argument("path")
    p_video.add_argument("--config", default="config.example.toml")
    p_video.add_argument("--start", type=int, default=None)
    p_video.add_argument("--end", type=int, default=None)
    p_video.set_defaults(fn=cmd_video)

    p_raw = sub.add_parser("raw")
    p_raw.add_argument("path")
    p_raw.add_argument("--config", default="config.example.toml")
    p_raw.set_defaults(fn=cmd_raw)

    p_run = sub.add_parser("run")
    p_run.set_defaults(fn=cmd_run)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
