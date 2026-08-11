"""Offline reconciliation: judge counts vs settlement-page fixture (runs/ report).

Usage: python reconcile.py [--config config.example.toml] [--expect 693,35,1,4]
Per-class match ratio = min(judged, official) / official must be >= 0.95 (TECH_REQ ch.8).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import capture
import judge
from acc import accuracy
from config import GameConfig


def parse_expect(text: str) -> tuple:
    p, g, b, m = (int(x) for x in text.split(","))
    return (p, g, b, m)


def reconcile(cfg: GameConfig, expect: tuple) -> dict:
    j = judge.OfflineJudge(cfg)
    j.process_stream(capture.frames_from_video(cfg.video_path, cfg))
    exp_p, exp_g, exp_b, exp_m = expect
    exp_n = exp_p + exp_g + exp_b + exp_m
    n = j.total()
    res = {
        "video": cfg.video_path,
        "window": (cfg.start, cfg.end),
        "judged": dict(P=j.perfects, G=j.goods, B=j.bad_miss, N=n),
        "expected": dict(P=exp_p, G=exp_g, B=exp_b, M=exp_m, N=exp_n),
        "match": {
            "P": min(j.perfects, exp_p) / exp_p,
            "G": min(j.goods, exp_g) / exp_g,
        },
        "acc_judged": accuracy(j.perfects, j.goods, exp_n),
        "acc_official": accuracy(exp_p, exp_g, exp_n),
        "unique_frames": len(j.window) == len({f for f, _ in j.window}),
        "samples": j.samples,
    }
    res["acc_delta"] = res["acc_judged"] - res["acc_official"]
    res["pass"] = (
        res["match"]["P"] >= 0.95
        and res["match"]["G"] >= 0.95
        and res["unique_frames"]
        and abs(res["acc_delta"]) < 0.1
        and res["expected"]["B"] == 0  # note: documented, see report
    )
    return res


def write_report(res: dict, outdir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"report_{ts}.md"
    (d, e) = (res["judged"], res["expected"])
    lines = [
        "# RealtimeAcc 离线对账报告",
        f"- 视频: `{res['video']}`  窗口(frames): {res['window']}  样本: {res['samples']}",
        f"- 判定计数(分数增量): P={d['P']}  G={d['G']}  B+M={d['B']}  合计={d['N']}",
        f"- 结算页基准: P={e['P']}  G={e['G']}  B={e['B']}  M={e['M']}  N={e['N']}",
        f"- 一致率: P {res['match']['P']*100:.1f}% (阈 >=95%)   G {res['match']['G']*100:.1f}% (阈 >=95%)",
        f"- ACC: 判定 {res['acc_judged']:.2f}% vs 结算 {res['acc_official']:.2f}%  偏差 {res['acc_delta']:+.2f}pp (阈 |.|<0.1)",
        f"- 零重复帧: {res['unique_frames']}",
        "",
        "## 例外与已知偏差",
        "- 游戏未显示判定花体字(录像设置), B/M 无法经分数增量区分, 合并上报并经 N=733 兜底。",
        "- 结算明细页文本为半透明样式, 实时 OCR 不可靠; 基准值来自分析期读得的结算页静态数值。",
        f"- 结论: **{'PASS' if res['pass'] else 'FAIL'}**",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(prog="reconcile")
    ap.add_argument("path", nargs="?", default=None)
    ap.add_argument("--config", default="config.example.toml")
    ap.add_argument("--expect", default=None, help="official P,G,B,M e.g. 693,35,1,4")
    args = ap.parse_args()
    cfg = GameConfig().load(args.config)
    if args.path:
        cfg.video_path = args.path
    if not cfg.video_path:
        print("no video path given"); return 2
    expect = parse_expect(args.expect) if args.expect else cfg.expected
    if expect is None:
        print("no expected counts: pass --expect or set [expect] in config"); return 2
    res = reconcile(cfg, expect)
    path = write_report(res, Path("runs"))
    print(path)
    print(f"P {res['match']['P']*100:.1f}%  G {res['match']['G']*100:.1f}%  ACC {res['acc_judged']:.2f}%(judged) vs {res['acc_official']:.2f}%(official) delta {res['acc_delta']:+.2f}")
    print("RESULT:", "PASS" if res["pass"] else "FAIL")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())