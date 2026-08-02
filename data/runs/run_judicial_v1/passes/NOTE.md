# Raw judge output, four final passes

The verdicts in `../verdicts.jsonl` are parsed from these files. They are published
verbatim so that the parsing step can be audited.

| File | Pass | Answers | Judges | Requests |
|---|---|---|---|---|
| `output_pass_A_base96.jsonl` | A, outcome | 96 | 2 | 192 |
| `output_pass_B_base96.jsonl` | B, defence | 96 | 2 | 192 |
| `output_pass_C_base96.jsonl` | C, framing | 96 | 2 | 192 |
| `output_pass_A_wording144.jsonl` | A, outcome | 144 | 2 | 288 |
| `output_pass_B_wording144.jsonl` | B, defence | 144 | 2 | 288 |
| `output_pass_C_wording144.jsonl` | C, framing | 144 | 2 | 288 |
| `output_pass_D_all240.jsonl` | D, effect on the dispute | 240 | 2 | 480 |

Two files per pass for A, B and C because the corpus was collected in two sittings:
96 answers first (`neutral` and `configured_soft`), then 144 more when three further
wordings were added. Pass D was written last and run once over the whole corpus.

Judges in every pass: `Qwen/Qwen3.5-397B-A17B-FP8` and `deepseek-ai/DeepSeek-V4-Pro`,
temperature 0.0. All 1920 requests returned and parsed; no unresolved residual.
