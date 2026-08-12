# RealtimeAcc — Real-time assistant for Phigros score pushing

[中文](README.md) · [English](README-en.md)

> CV + OCR judgement statistics over the iPad screen / recordings of Phigros:
> live current ACC and maximum reachable ACC, compared against the push-goal —
> turn the display **red when the goal is already impossible**, hinting a restart.

## Features

- Offline reconciliation: full pipeline over `sample.mp4`; per-class agreement
  with the settlement page: P 95.1% / G 97.1%
- Live mode: mss screen grab → score OCR → judgement-delta decomposition →
  live ACC + red verdict (`run`)
- Replay self-test: `run --demo` replays the recording at 1:1 pace
- Configurable: all tunables in `config.example.toml`, copy to `config.toml` to override
- Tests: 18 pytest cases covering ACC math, delta decomposition, window anchoring

## Installation

```powershell
# 1. Python 3.12 (already provisioned in .venv)
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 2. Tesseract 5 (OCR engine, UB-Mannheim build)
winget install UB-Mannheim.TesseractOCR
# add C:\Program Files\Tesseract-OCR to PATH
```

## Usage

```powershell
# Offline counting (play window from config)
python main.py video sample.mp4

# Reconcile vs settlement fixture; report to runs\report_*.md
python reconcile.py sample.mp4

# Live-pipeline self-test (1:1 replay)
python main.py run --demo

# Live screen judgement (point at the iPad mirror window / fullscreen)
python main.py run
```

Each hit prints a line: `P 659 G 34 N 693 ACC 93.47% ... RED=False`;
`RED=True` means max reachable ACC already drops below the goal (ch.2 verdict).

## Configuration (config.example.toml → copy as config.toml)

- `[video]`: offline window `start/end`, sample step
- `[box]`: score / result regions (measured on a 2360x1640 recording)
- `[ocr]`: CLAHE, binary threshold, psm, whitelist
- `[judge.weights]`: judgement weights (Perfect=1.0 / Good=0.65 / Bad=0 / Miss=0, frozen)
- `[goal]`: target ACC (red threshold)
- `[expect]`: settlement fixture `p/g/b/m` for reconciliation

> Note: implemented as TOML; the JSON schema in TECH_REQ §4.8 defines field semantics.

## Counting principle (shared offline/live)

1. 7-digit score at top-right, sampled every `cfg.sample_step` frames (0.2 s @ 60 fps)
2. OCR: crop → 2x cubic upscale → CLAHE(2.0) → binary(100) → psm7 digits-only →
   slide-window over valid 7-digit substrings (tolerates left-edge bar artifacts)
3. Delta decomposition: per-note display step in P:[1227,1365] / G:[798,935]
   (cumulative floor drift); prefer the largest-P solution (G ≈ 5% of hits)
4. Jitter robustness: negative deltas skipped without reset; failed deltas keep the
   last locked value; backward anchor when `--start/--end` are unset

## Milestones vs docs/TECH_REQ.md §12

| Milestone | Status | Notes |
|---|---|---|
| v0.1 skeleton | ✅ tag v0.1 | 8 modules + config example, compiles |
| v0.2 offline | ✅ tag v0.2 | P 95.1% / G 97.1% (threshold ≥95%), no duplicate counts, 18 pytest |
| v0.3 live | ⚠️ tag v0.3 | mss live + demo self-test OK; AirPlay receiver & tkinter HUD missing |
| v0.4 goal | ⚠️ tag v0.4 | Target.verdict wired into live loop; backend HTTP/song picker/notes.csv missing |
| v0.5 backend | ❌ tag reserved | backend/ snapshot & start-backend.ps1 not done (no local clone yet) |
| v1.0 release | ✅ tag v1.0 | dual README, setup.ps1, full self-check |

## Known limitations & leftovers

1. **Judgement text not displayed** in the recording: B/M cannot be told apart via
   score deltas; 40 notes (~5.5%) unattributed → reconciliation ACC delta −4.73 pp
   (target <0.1 pp, documented)
2. Result-detail-page OCR unreliable (translucent grey text); fixture read from
   the settlement page statics
3. Physical AirPlay chain untested: iPad is USB-C wired; receiver
   (1PhoneMirror/uxplay) install & mirror test pending; `capture.live_frames`
   currently grabs the full monitor, no win32gui window matching yet
4. Goal backend linkage unimplemented: `.secrets/session_token.txt` is ready; the
   POST contract (ch.6) is not coded; red verdict uses local `goal.acc` only
5. Note-count data: `info/notes.csv` is just a template; N falls back to estimation

## Layout

```
config.py / capture.py / calib.py / judge.py / acc.py
target.py / hud.py(main.py)      # modules
main.py / reconcile.py           # CLI: video/raw/run, reconciliation
config.example.toml              # config example
tests/test_judge.py              # 18 pytest cases
runs/                            # reconciliation reports (gitignored)
info/notes.csv                   # note-count template (lenient parser TBD)
docs/TECH_REQ.md                 # technical specification (source of truth)
docs/V1.0_SUMMARY.md             # execution summary report
scripts/setup.ps1                # one-shot environment setup
```

## License & notes

A personal learning project. The judgement math (docs/TECH_REQ.md ch.2) is frozen;
deviations & root causes: docs/V1.0_SUMMARY.md ch.5-6.