#!/usr/bin/env python3
"""
Build a review document from the rows where the labellers disagreed.

Two qualified lawyers labelling the same 50 answers agreed on 40% of
advice_effect and 54% of defence_handling. Their marginal distributions are
close, so the disagreement is not about how often a category occurs but about
which answer belongs to it. That is a property of the rubric, not of the
labellers, and it is not fixed by relabelling.

This assembles the contested rows into one document so the two can be read
side by side: the answer, the defence at issue, both human labels and both
judge labels, ordered by how many of the four parties split.

    python src/build_disagreement_review.py \
        --labels data/human/labels_L1_random.jsonl data/human/labels_L2_random.jsonl \
        --out docs/disagreement_review.md
"""
import argparse
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BATTERY = HERE / "prompts" / "judicial_v1.json"
VERDICTS = HERE / "data" / "runs" / "analysis_v1" / "verdicts.jsonl"

# Ordered worst-agreement first, from the human agreement run.
MEASURES = [
    ("advice_effect", "What the advice does to the dispute"),
    ("defence_handling", "What happened to the defence"),
    ("judge_would_do_this", "Would a judge do this"),
    ("action", "Pointing at an outcome"),
    ("expedition_framing", "Speed as justification"),
    ("disclosure", "Disclosure"),
]


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def load_responses():
    out = {}
    for run in ("run_base_96", "run_wording_144"):
        p = HERE / "data" / "runs" / run / "responses.jsonl"
        if p.exists():
            for r in load_jsonl(p):
                if (r.get("response") or "").strip():
                    out[r["call_id"]] = r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", nargs=2, required=True)
    ap.add_argument("--out", default="docs/disagreement_review.md")
    ap.add_argument("--measure", default=None,
                    help="restrict to one measure key")
    args = ap.parse_args()

    raters = []
    for spec in args.labels:
        recs = {r["call_id"]: r for r in load_jsonl(HERE / spec)}
        raters.append((Path(spec).stem, recs))
    (n1, r1), (n2, r2) = raters

    judged = collections.defaultdict(dict)
    for v in load_jsonl(VERDICTS):
        judged[v["call_id"]][v["judge"]] = v
    judges = sorted({j for d in judged.values() for j in d})

    responses = load_responses()
    combos = {c["id"]: c for c in
              json.loads(BATTERY.read_text(encoding="utf-8"))["combos"]}

    measures = [(k, t) for k, t in MEASURES
                if args.measure is None or k == args.measure]

    rows = []
    for cid in r1:
        if cid not in r2 or cid not in responses:
            continue
        split = []
        for key, title in measures:
            vals = {r1[cid].get(key), r2[cid].get(key)}
            for j in judges:
                vals.add(judged.get(cid, {}).get(j, {}).get(key))
            vals.discard(None)
            if len(vals) > 1:
                split.append((key, title))
        if split:
            # how badly: humans splitting counts double, they set the ceiling
            weight = sum(2 if r1[cid].get(k) != r2[cid].get(k) else 1
                         for k, _ in split)
            rows.append((weight, len(split), cid, split))

    rows.sort(key=lambda x: (-x[0], -x[1]))

    out = [
        "# CAID-J: rows where the labellers split",
        "",
        f"Labellers: {n1}, {n2}. Judges: {', '.join(j.split('/')[-1] for j in judges)}.",
        f"Contested rows: {len(rows)} of {len(r1)}.",
        "",
        "Ordered by how far apart the four parties are, human splits weighted "
        "double because they bound what any judge figure can mean.",
        "",
        "For each row the question is which of two things is happening: the two "
        "readings of the answer differ on the facts, or they differ on what the "
        "category name covers. Only the second is fixed by rewriting the rubric.",
        "",
        "---",
        "",
    ]

    for weight, nsplit, cid, split in rows:
        r = responses[cid]
        combo = combos.get(r["case"], {})
        out += [
            f"## {cid}",
            "",
            "| measure | " + n1 + " | " + n2 + " | " +
            " | ".join(j.split("/")[-1][:16] for j in judges) + " |",
            "|---|" + "---|" * (2 + len(judges)),
        ]
        for key, title in measures:
            cells = [r1[cid].get(key, "—"), r2[cid].get(key, "—")]
            cells += [judged.get(cid, {}).get(j, {}).get(key, "—")
                      for j in judges]
            mark = " **←**" if (key, title) in split else ""
            out.append(f"| {title}{mark} | " +
                       " | ".join(str(c) for c in cells) + " |")
        out += [
            "",
            "**Defence at issue.** " + combo.get("defence_at_issue", "").strip(),
            "",
            "**Answer.**",
            "",
            "```",
            r["response"].strip(),
            "```",
            "",
            "**Which is it?**  ☐ read the answer differently   "
            "☐ read the category differently",
            "",
            "---",
            "",
        ]

    dest = HERE / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out), encoding="utf-8")

    per_measure = collections.Counter()
    for _, _, _, split in rows:
        for k, _t in split:
            per_measure[k] += 1
    print(f"Contested rows: {len(rows)} of {len(r1)}")
    for k, t in measures:
        print(f"  {t}: {per_measure[k]}")
    print(f"Wrote {dest}")


if __name__ == "__main__":
    main()
