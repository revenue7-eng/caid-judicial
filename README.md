# CAID-J

Judicial dual-condition behavioural testing. A benchmark for measuring how much of an AI assistant's behaviour in a judicial support role comes from the deployed system prompt rather than from the model.

Run a frozen battery of case files twice: once under a neutral system prompt, once under the prompt you intend to deploy. The delta is the finding. Judge both sets with a model held outside your roster, one question per pass, two judges, and report the disagreement.

This is CAID-J v1.0. Derived from the [CAID protocol](https://github.com/revenue7-eng/caid-benchmark) (MIT), which does the same for commercial deployments. What differs, and why the commercial violation definition does not transfer, is set out in [`PROTOCOL.md`](PROTOCOL.md) §1a.

**Licence:** MIT.

---

## What problem this solves

A court administration buys an AI assistant for case support. Someone writes its system prompt, and a sentence about caseload finds its way in: the court is busy, help matters move toward timely resolution. Nothing unlawful, nothing adversarial, and it passes any safety review.

The judge never sees that sentence, and neither does whoever signed off the procurement. No individual answer looks wrong afterwards, because none of them is.

The only way to see what the sentence did is to run the same cases without it and read the two sets side by side. That comparison is possible before go-live and not after, because after go-live the second version of the answer does not exist.

CAID-J is that comparison, specified so it can be audited.

---

## Reference run

Four frontier models, four synthetic UAE civil matters, five conditions, 240 answers, 1440 verdicts from two independent judges.

| Measure | Neutral | Shift under configuration | p |
|---|---|---|---|
| Any advice to the court | 27/48 and 8/48 | +29.7 and +33.3 pp | <0.0001 |
| Advice narrows the dispute or further | 4/48 and 0/48 | +26.0 and +22.4 pp | <0.0001 |
| Speed as justification | 4/48 and 8/48 | +76.0 and +70.3 pp | <0.0001 |
| Advice cuts into defence or decides | 1/48 and 0/48 | +3.1 and +4.2 pp | 0.108 / 0.015 |
| Pointing at an outcome | 6/48 and 5/48 | +15.1 and +4.2 pp | <0.0001 / 0.205 |

Two figures per cell, one per judge. Shifts are means over 64 model-and-case pairs.

The instruction reliably changes how much the assistant advises and how far its advice narrows the dispute. It does not measurably make the advice worse: disposal on the merits appears zero times in 480 verdicts, and 275 of 296 advice items are marked as something a competent judge would properly do. Outcome-steering held under one wording and collapsed under three, and is not a result of this run.

Full account with methodology, uncertainty and limitations: [`REPORT.md`](REPORT.md).

This run is not claimed to be CAID-J conformant. The judges are not validated against human gold labels (PROTOCOL §5), and the battery has no allowed-action scenarios, so overrefusal is unmeasured (PROTOCOL §6). Both gaps are stated in the report.

---

## Running it

```
export OPENROUTER_API_KEY="..."

./run_full_pipeline.sh --smoke        # 1 model, 1 case, sanity check
./run_full_pipeline.sh --n 3          # full factorial
```

Collection writes `data/runs/<run-id>/responses.jsonl` and builds four judge batch files. Upload those to a batch-capable OpenAI-compatible endpoint, save the results alongside them as `output_pass_A.jsonl` through `output_pass_D.jsonl`, then:

```
./run_full_pipeline.sh --parse <run-id>
```

That parses the verdicts, computes metrics with pair-level significance, and prints the tables a conformant report must contain.

Interrupted collection resumes with `./run_full_pipeline.sh --resume <run-id>`. Rows already on disk with a non-empty answer are skipped; rows that came back empty are re-issued.

Standard library only, no dependencies.

The pipeline was verified end to end on a smoke run before publication. The reference corpus in `data/runs/run_judicial_v1/` was collected in two sittings before the pipeline was written, and was not regenerated through it; see REPORT.md under Reproducibility. Regenerating it would not reproduce those answers in any case, since generation runs above temperature zero.

### Auditing your own deployed prompt

Put it into `prompts/judicial_v1.json` as an additional entry under `system_prompts`, keep `neutral` unchanged, and run. Replace the cases with matters representative of your docket, keeping the shape required by PROTOCOL §3: the claimant's core fact admitted, the respondent raising a substantive defence.

If you test only your one deployed wording, the run is still conformant, but PROTOCOL §2a requires the report to say that the result is a property of that wording rather than of instructions of that kind. The reference run shows why: one measure survived rewording and another did not.

---

## What the benchmark refuses to do

The runner stops if a judge is one of the models under test, because a judge scoring itself makes any result in its favour worthless.

The analysis warns and blocks per-model rankings if a measure saturates at 100%, since at the ceiling a delta of zero means saturation in both conditions rather than resistance. That failure happened during development, and both superseded judge instructions are published in `prompts/` with the numbers they produced.

It warns where judge agreement on a label is low, and the report format then permits deltas only, not absolute shares.

It prints an upper bound rather than an absence wherever a measure records zero events.

---

## Layout

```
PROTOCOL.md                      normative specification, MUST clauses, conformance
REPORT.md                        reference run findings
prompts/
  judicial_v1.json               frozen battery
  judge_pass_A_outcome.txt       did the answer point at an outcome
  judge_pass_B_defence.txt       what happened to the defence
  judge_pass_C_framing.txt       speed as justification, disclosure
  judge_pass_D_effect.txt        what the advice does to the dispute
  superseded_*.txt               earlier judge instructions, kept with their failure figures
src/
  run_benchmark.py               response collection, resumable
  judge_batch.py                 build the four batches, parse the outputs
  analyze.py                     metrics, pair-level significance, agreement, guards
run_full_pipeline.sh
docs/
  FUTURE_EXPERIMENTS.md          what this run could not settle
data/runs/run_judicial_v1/
  responses.jsonl                240 answers, verbatim
  verdicts.jsonl                 480 records, both judges, all four passes
  rows.csv summary.csv           tables regenerated by analyze.py
  judge_agreement.csv            per-measure agreement between the judges
  run_config.json                models, conditions, decoding parameters
  passes/                        raw judge output for the four final passes
  superseded/                    three discarded judge instructions with their output
```

The prompts under `superseded/` are published because each failed in a way that is
easy to repeat: one saturated at 100% and made the least resistant model look like the
most resistant, and two more degraded the hardest label by asking several questions in
one call. Their notes carry the numbers.

---

## Citing

Andrey Lazarev, "CAID-J v1.0: Configuration-Induced Behavioural Shift in Judicial Case Support", 2026. MIT licence.

A publication claiming conformance must cite the protocol version and state which MUST clauses, if any, are unmet.
