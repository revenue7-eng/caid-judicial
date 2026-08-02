# Superseded judge instructions

Three judge instructions were written and discarded before the four-pass design in
`prompts/`. Each is published with its raw output, because each failed in a way that
would be easy to repeat.

All three were run against the same 96 answers: the four cases under `neutral` and
`configured_soft`. Judge model in every case: `Qwen/Qwen3.5-397B-A17B-FP8`,
temperature 0.0.

## j1_combined_label

One action label covering both pointing at an outcome and giving procedural
directions, plus disclosure and speed as justification. Three labels in one call.

Result: the action label reached 100% in the configured condition on all four models.
At that ceiling the delta is fixed by the neutral rate alone. `anthropic/claude-opus-5`
showed a shift of exactly zero and read as the most resistant model, when in fact it
advised in 12 of 12 neutral runs and there was nothing left for the instruction to add.

This is why PROTOCOL 6b requires a saturation warning and forbids per-model rankings
at the ceiling.

## j2_three_labels

The action label split in two: `steer_outcome` and `direct_procedure`. Disclosure and
speed as justification retained in the same call.

Result: usable, and the numbers here are the ones the split was designed to recover.
Superseded only because the defence axis was still missing and because three labels in
one call turned out to degrade the hardest of them.

Divergence against the single-question pass on the outcome label: 7%.

## j3_four_labels

The defence axis added alongside the other three. Four labels in one call.

Result: the judge began quoting section headings rather than the sentences that
decided the classification. On one row both this judge and the single-question pass
quoted the same sentence and assigned different labels. The outcome measure fell from
+25.0 pp to +12.3 pp on the same data.

Divergence against the single-question pass on the outcome label: 10%.

This is why PROTOCOL 5 requires one question per pass.

## Reading the raw output

Each folder holds `judge_prompt.txt`, `judge_output.jsonl` as returned by the batch
endpoint, and `custom_id_map.json` mapping request identifiers back to answers.
