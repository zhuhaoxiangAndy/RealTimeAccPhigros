"""RealtimeAcc CLI:
    python main.py video <path> [--config config.example.toml] [--start N] [--end N]
    python main.py raw   <path>   (print raw score reads; debugging)
    python main.py run            (live screen mode; v0.3+)
    python main.py run --demo     (replay the configured video at 1x; self-test)
"""
from __future__ import annotations

import argparse
import sys
import time

import capture
import judge
from acc import is_red
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


def _live_run(cfg, demo: bool) -> int:
    """Real-time loop: score-delta decomposition with a status line per hit."""
    import cv2

    if demo:
        if not cfg.video_path:
            print("--demo needs [video] video_path in config")
            return 2
        frames = capture.frames_from_video(cfg.video_path, cfg)

        def stream():
            for f in frames:
                yield f
                time.sleep(cfg.sample_step / cfg.fps)
    else:
        def stream():
            yield from capture.live_frames(cfg)

    prev = None
    P = G = 0
    t0 = time.monotonic()
    frames_done = 0
    for _idx, frame in stream():
        score = judge.ocr_score(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cfg)
        if score is None:
            continue
        frames_done += 1
        if prev is not None:
            delta = score - prev
            if delta <= 0:
                continue
            if delta <= cfg.delta_cap:
                hit = judge.decompose_delta(delta, cfg)
                if hit is not None:
                    P += hit[0]
                    G += hit[1]
                    prev = score
                    n = P + G
                    acc = (P + 0.65 * G) / n * 100.0 if n else 0.0
                    from target import Target

                    red = Target.from_config(cfg).verdict(P, G, n)
                    dt = (time.monotonic() - t0) / max(1, frames_done) * 1000
                    print(f"P {P:>3}  G {G:>3}  N {n:>3}  ACC {acc:6.2f}%"
                          f"  {dt:5.0f}ms/f  RED={red}")
                    continue
            prev = None
            continue
        prev = score
    return 0


def cmd_run(args) -> int:
    cfg = GameConfig().load(args.config)
    return _live_run(cfg, args.demo)


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
    p_run.add_argument("--demo", action="store_true")
    p_run.add_argument("--config", default="config.example.toml")
    p_run.set_defaults(fn=cmd_run)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())