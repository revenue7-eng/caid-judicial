# How the runs are organised

Two collections of answers and one analysis over both.

```
run_base_96/        first sitting: neutral and configured_soft, 96 answers
run_wording_144/    second sitting: terse, resource and blunt, 144 answers
analysis_v1/        verdicts and tables over all 240
```

## Why two collections

The first sitting tested one configured wording against a neutral baseline. That
design cannot tell a property of one sentence apart from a property of a class of
instructions, and the distinction turned out to matter: outcome-steering held under
that wording and collapsed under the three added later, while speed as justification
held under all four.

The second sitting added three more wordings of the same intent. It has no neutral
condition of its own; every comparison runs against the neutral answers in
`run_base_96`. That is what `compared_against` in its config records.

PROTOCOL 2a now requires at least three configured wordings for any claim about a
class of instructions. It was written because of this sequence.

## Why the analysis is separate

Passes A, B and C were run on each collection as it arrived, and their raw output
lives with the collection it judged. Pass D was written last, once it became clear
that measuring how much a model advises says nothing about whether the advice is
harmful. It was run once over both corpora, so it belongs to neither and sits under
`analysis_v1/passes/`.

`analysis_v1/` holds no answers of its own. It reads them from the two collections
named in its `run_config.json`.

## Recomputing

```
python3 src/analyze.py --run-id analysis_v1
```

Collections are taken from `inputs` in the analysis config. To analyse one collection
alone, name it explicitly:

```
python3 src/analyze.py --run-id analysis_v1 --corpus run_base_96
```

## Superseded judges

Three judge instructions were tried and discarded before the four-pass design. All
three judged `run_base_96`, so they live under it, in `superseded/`, each with its raw
output and a note on how it failed.
