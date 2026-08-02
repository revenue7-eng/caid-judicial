# Raw judge output, collection run_base_96

The verdicts in `../../analysis_v1/verdicts.jsonl` are parsed from these files and
from the matching files under `../../run_wording_144/passes/` and
`../../analysis_v1/passes/`. They are published verbatim so the parsing step can be
audited.

| File | Pass | Answers | Judges | Requests |
|---|---|---|---|---|
| `output_pass_A.jsonl` | A, outcome | 96 | 2 | 192 |
| `output_pass_B.jsonl` | B, defence | 96 | 2 | 192 |
| `output_pass_C.jsonl` | C, framing | 96 | 2 | 192 |

Judges: `Qwen/Qwen3.5-397B-A17B-FP8` and `deepseek-ai/DeepSeek-V4-Pro`, temperature
0.0. Pass D for these answers is in `../../analysis_v1/passes/`, because it was run
once over both collections.
