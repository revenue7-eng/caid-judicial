# Open questions

Recorded so that the next run starts from what this one could not settle.

## 1. Human calibration of the judges

PROTOCOL 5 requires an agreement figure against human gold labels for full
conformance, and this run has none. All 1440 verdicts come from two language models.

What is needed is one set of roughly fifty hand-labelled answers, scored blind against
the same four questions, and a per-measure agreement figure against each judge. It is a
one-time exercise and does not grow with the corpus. It does not carry over from
another domain, because the labels differ.

The sample should be weighted toward the rows where the two judges disagree, plus a
control group where they agree, so that the figure measures the boundary rather than
the easy cases.

## 2. Cases where the defence is implied rather than pleaded

Every combo in the reference battery states the respondent's defence openly in the
material the model receives. That is the easiest condition for a defence to survive,
and the negative result on defence displacement was obtained there.

A battery of cases where the defence is implicit, poorly articulated, or buried in a
narrative would test the same hypothesis where it has a chance of confirming. Until
that is run, the 4% upper bound applies to pleaded defences only.

## 3. Overrefusal

The battery contains no scenarios where a substantive answer is allowed and expected.
A model could therefore score well on every measure here by refusing to engage, and
nothing in the current design would catch it.

Adding allowed-action combos would let the two axes be reported together, as the
commercial protocol requires.

## 4. Multi-turn

Everything here is single turn against a fixed file. A deployed assistant is asked
follow-up questions, and the interesting question is whether a configuration that
shifts nothing on turn one shifts something by turn four.

## 5. Language

Nothing was tested in Arabic, and the cases are set in a jurisdiction where Arabic is
the language of the courts. Whether the effect survives translation of both the
instruction and the case file is unknown.

## 6. Model coverage

Four frontier general-purpose assistants. No specialised legal models, no smaller
models, no open-weight family sweep. The spread between the four on the strongest
measure reaches 42 pp, so the population is not uniform and four is a small sample of
it.

## 7. Whether the shift compounds

Each measure here is a rate over independent answers. Nobody has asked what happens
across a docket: whether a small consistent lean, applied to every matter of one kind,
accumulates into something visible at the level of case outcomes. That is a different
study and probably needs real disposal data rather than synthetic files.
