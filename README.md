# CAID-J

Judicial dual-condition behavioural testing. A benchmark for measuring how much of an AI assistant's behaviour in a judicial support role comes from the deployed system prompt rather than from the model.

Run a frozen battery of case files twice: once under a neutral system prompt, once under the prompt you intend to deploy. The delta is the finding. Judge both sets with a model held outside your roster, one question per pass, two judges, and report the disagreement.

New here? Start with [How the measurement works](docs/how-it-works.md) ([PDF](docs/how-it-works.pdf)).  
Ready to run it? [Running it yourself](docs/run-it-yourself.md) ([PDF](docs/run-it-yourself.pdf)).

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

The five conditions are the neutral prompt and four wordings of the same instruction: soft, terse, resource-framed and blunt. Four wordings rather than one, so that a result can be a property of the instruction rather than of a sentence.

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

Each answer is judged four times, one question per pass: whether it pointed at an outcome (A), what it did with the defence (B), whether it justified itself by speed and whether it disclosed (C), and what the advice does to the dispute (D). Separate passes because several labels in one call degrade the hardest of them.

Collection writes `data/runs/<run-id>/responses.jsonl` and builds four judge batch files. Upload those to a batch-capable OpenAI-compatible endpoint, save the results alongside them as `output_pass_A.jsonl` through `output_pass_D.jsonl`, then:

```
./run_full_pipeline.sh --parse <run-id>
```

That parses the verdicts, computes metrics with pair-level significance, and prints the tables a conformant report must contain.

Interrupted collection resumes with `./run_full_pipeline.sh --resume <run-id>`. Rows already on disk with a non-empty answer are skipped; rows that came back empty are re-issued.

Standard library only, no dependencies.

The pipeline was verified end to end on a smoke run before publication. The reference corpus is published in full.

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
data/runs/
  NOTE.md                        how the collections and the analysis relate
  run_base_96/                   first sitting: neutral and configured_soft
    responses.jsonl              96 answers, verbatim
    passes/                      raw judge output, passes A to C
    superseded/                  three discarded judge instructions with their output
  run_wording_144/               second sitting: terse, resource, blunt
    responses.jsonl              144 answers
    passes/                      raw judge output, passes A to C
  analysis_v1/                   analysis over both collections
    passes/                      raw judge output, pass D
    verdicts.jsonl               480 records, both judges, all four passes
    rows.csv summary.csv         tables regenerated by analyze.py
    judge_agreement.csv          per-measure agreement between the judges
```

The corpus arrived in two sittings. The first tested one configured wording; the
second added three more, once it became clear that one wording cannot support a claim
about a class of instructions. The second collection has no neutral condition of its
own and is compared against the first. Pass D was written last and run over both,
which is why it sits under the analysis rather than under either collection.

The prompts under `superseded/` are published because each failed in a way that is
easy to repeat: one saturated at 100% and made the least resistant model look like the
most resistant, and two more degraded the hardest label by asking several questions in
one call. Their notes carry the numbers.

---

## Contributions

The study design originates with Mohammed Zoheb Shaik: testing a deployed configuration
against a neutral baseline, on the argument set out in "Zero Trust for the System Prompt"
(2026). The four case files and both axes of the scoring rubric are his; axis I/R became
the split between steering the outcome and directing procedure, axis L/D became the
judging pass on what the answer does with the defence.

Data collection, the judging pipeline and the statistical analysis are by Andrey Lazarev.

---

## Citing

Andrey Lazarev and Mohammed Zoheb Shaik, "CAID-J v1.0: Configuration-Induced
Behavioural Shift in Judicial Case Support", 2026. MIT licence.

A publication claiming conformance must cite the protocol version and state which MUST clauses, if any, are unmet.
