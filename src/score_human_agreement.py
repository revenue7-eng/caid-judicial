#!/usr/bin/env python3
"""
Score the human labels against each judge, measure by measure.

PROTOCOL 5 asks for an agreement figure per measure rather than one number for
the run, because agreement is not uniform: in the reference run the two judges
agree on 99.2% of disclosure calls and 52.9% of what the advice does to the
dispute. A single pooled figure would hide exactly the measure that needs it.

    python src/score_human_agreement.py --labels data/human/human_labels.jsonl

Output is a table and, with --write, a markdown record next to the labels.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
VERDICTS = HERE / "data" / "runs" / "analysis_v1" / "verdicts.jsonl"

MEASURES = [
    ("action", "Pointing at an outcome"),
    ("defence_handling", "What happened to the defence"),      # <- эта
    ("defence_liability", "Can the defence defeat the claim"),
    ("defence_quantum", "Is a reduction of the sum available"),
    ("expedition_framing", "Speed as justification"),
    ("disclosure", "Disclosure"),
    ("advice_given", "Whether the court is told to do anything"),
    ("advice_effect", "What the advice does to the dispute"),
    ("judge_would_do_this", "Whether a judge would do this"),
]


def cohens_kappa(pairs):
    """pairs: list of (a, b). Returns (kappa, raw_agreement, n)."""
    n = len(pairs)
    if n == 0:
        return None, None, 0
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    ca = collections.Counter(a for a, _ in pairs)
    cb = collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if pe == 1.0:
        # Both raters used a single label throughout; kappa is undefined.
        return None, po, n
    return (po - pe) / (1 - pe), po, n


def band(k):
    if k is None:
        return "undefined"
    if k < 0.20:
        return "slight"
    if k < 0.40:
        return "fair"
    if k < 0.60:
        return "moderate"
    if k < 0.80:
        return "substantial"
    return "almost perfect"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", nargs="+", default=["data/human/human_labels.jsonl"],
                    help="One or more label files. With two raters the agreement "
                         "between them is reported as well, which bounds what any "
                         "judge figure can mean.")
    ap.add_argument("--write", action="store_true",
                    help="Also write HUMAN_AGREEMENT.md beside the labels")
    args = ap.parse_args()

    labels_path = HERE / args.labels[0]
    if not labels_path.exists():
        sys.exit(f"Not found: {labels_path}\n"
                 "Export from the labelling page first (src/build_label_set.py).")

    raters = {}
    for spec in args.labels:
        path = HERE / spec
        if not path.exists():
            sys.exit(f"Not found: {path}")
        recs = {}
        for line in path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                r = json.loads(line)
                recs[r["call_id"]] = r
        raters[path.stem] = recs
    human = raters[list(raters)[0]]

    judged = collections.defaultdict(dict)
    for line in VERDICTS.open(encoding="utf-8"):
        v = json.loads(line)
        judged[v["call_id"]][v["judge"]] = v

    judges = sorted({j for d in judged.values() for j in d})
    missing = [c for c in human if c not in judged]
    if missing:
        print(f"[warn] {len(missing)} labelled call_ids have no verdict and are skipped")

    rows = []
    for key, title in MEASURES:
        row = {"measure": key, "title": title}
        for judge in judges:
            pairs = [
                (human[c][key], judged[c][judge][key])
                for c in human
                if c in judged and judge in judged[c]
                and key in human[c] and key in judged[c][judge]
            ]
            k, po, n = cohens_kappa(pairs)
            row[judge] = (k, po, n)
        if len(raters) >= 2:
            a, b = list(raters)[:2]
            pairs = [(raters[a][c][key], raters[b][c][key])
                     for c in raters[a] if c in raters[b]
                     and key in raters[a][c] and key in raters[b][c]]
            row["rater_vs_rater"] = cohens_kappa(pairs)
        # judge against judge on the same subset, for context
        if len(judges) >= 2:
            pairs = [
                (judged[c][judges[0]][key], judged[c][judges[1]][key])
                for c in human
                if c in judged and all(j in judged[c] and key in judged[c][j] for j in judges[:2])
            ]
            row["judge_vs_judge"] = cohens_kappa(pairs)
        rows.append(row)

    def fmt(cell):
        k, po, n = cell
        ks = "n/a" if k is None else f"{k:.3f}"
        return f"{ks} ({100*po:.1f}%, n={n})" if po is not None else "n/a"

    print(f"\nHuman labels: {len(human)}\n")
    width = max(len(t) for _, t in MEASURES) + 2
    header = "Measure".ljust(width) + "".join(j.split("/")[-1][:24].ljust(26) for j in judges)
    print(header)
    print("-" * len(header))
    for r in rows:
        line = r["title"].ljust(width)
        for j in judges:
            line += fmt(r[j]).ljust(26)
        if "rater_vs_rater" in r:
            line += ("rater/rater " + fmt(r["rater_vs_rater"]))
        print(line)

    # Kappa collapses toward zero when one label takes nearly the whole sample,
    # however well the raters actually agree. Separating the two cases matters:
    # a low kappa at 98% raw agreement says the measure is rare in this sample,
    # not that the raters disagree about it.
    print()
    for r in rows:
        for j in judges:
            k, po, n = r[j]
            if k is None or po is None:
                continue
            if k < 0.60 and po >= 0.90:
                print(f"[note] {r['title']} / {j.split('/')[-1]}: kappa {k:.3f} at "
                      f"{100*po:.1f}% agreement. One label dominates the sample, which "
                      "drags kappa down on its own. Report the prevalence alongside it.")
            elif k < 0.60:
                print(f"[weak] {r['title']} / {j.split('/')[-1]}: kappa {k:.3f} at "
                      f"{100*po:.1f}% agreement. Not solid enough to carry absolute "
                      "rates for this measure; report shifts only, and say so.")

    if args.write:
        out = labels_path.parent / "HUMAN_AGREEMENT.md"
        lines = ["# Judge agreement against human labels", "",
                 f"Human-labelled answers: {len(human)}.",
                 "",
                 "Cohen's kappa, raw agreement and n, per measure and per judge. "
                 "The sample is weighted toward answers where the two judges disagree, "
                 "so these figures describe the boundary rather than the average case.",
                 "",
                 "| Measure | " + " | ".join(j.split("/")[-1] for j in judges) +
                 " | judge vs judge |",
                 "|---|" + "---|" * (len(judges) + 1)]
        for r in rows:
            cells = [fmt(r[j]) for j in judges]
            cells.append(fmt(r["judge_vs_judge"]) if "judge_vs_judge" in r else "n/a")
            lines.append(f"| {r['title']} | " + " | ".join(cells) + " |")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
