#!/usr/bin/env python3
"""
CAID-J judge pipeline: four single-question passes, two independent judges.

Build the batch files:

    python src/judge_batch.py --run-id my_run --build

Upload each batch_pass_*.jsonl to a batch-capable OpenAI-compatible endpoint,
download the outputs next to them as output_pass_*.jsonl, then parse:

    python src/judge_batch.py --run-id my_run --parse

Writes data/runs/<run-id>/verdicts.jsonl.

PROTOCOL 5 requires one question per pass, the same judge across a whole
corpus, at least two judges from different developers, and a judge that is not
one of the models under test. This script enforces the last of those and warns
on the others.
"""

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATTERY = os.path.join(ROOT, "prompts", "judicial_v1.json")

PASSES = {
    "A": ("judge_pass_A_outcome.txt", ["action"]),
    "B": ("judge_pass_B_defence_v3.txt", ["defence_liability", "defence_quantum"]),
    "C": ("judge_pass_C_framing.txt", ["disclosure", "expedition_framing"]),
    "D": ("judge_pass_D_effect_v2.txt", ["advice_given", "advice_effect", "judge_would_do_this"]),
}
KEY_PHRASES = ["key_phrase_action", "key_phrase_defence",
               "key_phrase_disclosure", "key_phrase_expedition",
               "key_phrase_effect"]

DEFAULT_JUDGES = ["Qwen/Qwen3.5-397B-A17B-FP8", "deepseek-ai/DeepSeek-V4-Pro"]


def fill(template, battery, combo, response_text):
    task = battery["user_task"].format(case=combo["case_file"])
    return (template
            .replace("{defence}", combo["defence_at_issue"])
            .replace("{user_prompt}", task)
            .replace("{response_text}", response_text))


def build(run_dir, battery, judges, max_tokens, passes="A,B,C,D"):
    responses = [json.loads(l) for l in
                 open(os.path.join(run_dir, "responses.jsonl"), encoding="utf-8")]
    responses = [r for r in responses if (r.get("response") or "").strip()]
    combos = {c["id"]: c for c in battery["combos"]}

    tested = set(battery.get("reference_models", []))
    tested |= {r["model"] for r in responses}
    for j in judges:
        if j in tested:
            sys.exit(f"REFUSING TO BUILD: judge {j} is one of the models under test.\n"
                     "PROTOCOL 5: a judge scoring itself makes any result in its favour "
                     "worthless. Choose a judge outside the roster.")
    if len(judges) < 2:
        print("[note] fewer than two judges. PROTOCOL 5 requires at least two from "
              "different developers, with agreement reported.")

    wanted = {t.strip().upper() for t in passes.split(",") if t.strip()}
    unknown = wanted - set(PASSES)
    if unknown:
        sys.exit(f"Unknown pass: {', '.join(sorted(unknown))}")

    for tag, (prompt_file, _) in PASSES.items():
        if tag not in wanted:
            continue
        template = open(os.path.join(ROOT, "prompts", prompt_file), encoding="utf-8").read()
        for ph in ("{user_prompt}", "{response_text}"):
            if ph not in template:
                sys.exit(f"{prompt_file} is missing {ph}")
        if tag == "B" and "{defence}" not in template:
            sys.exit(f"{prompt_file} is missing {{defence}}")

        id_map, n = {}, 0
        batch_path = os.path.join(run_dir, f"batch_pass_{tag}.jsonl")
        with open(batch_path, "w", encoding="utf-8") as bf:
            for r in responses:
                content = fill(template, battery, combos[r["case"]], r["response"])
                for judge in judges:
                    cid = f"{tag.lower()}{n:05d}"
                    bf.write(json.dumps({
                        "custom_id": cid, "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": {"model": judge,
                                 "messages": [{"role": "user", "content": content}],
                                 "max_tokens": max_tokens, "temperature": 0.0},
                    }, ensure_ascii=False) + "\n")
                    id_map[cid] = {"call_id": r["call_id"], "judge": judge, "pass": tag}
                    n += 1
        json.dump(id_map, open(os.path.join(run_dir, f"id_map_pass_{tag}.json"),
                               "w", encoding="utf-8"), indent=1)
        print(f"pass {tag}: {n} requests -> {os.path.basename(batch_path)}")

    print(f"\nUpload the four batch_pass_*.jsonl files, save the results next to them "
          f"as output_pass_A.jsonl ... output_pass_D.jsonl, then run --parse")


def extract(text, fields):
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    out = {}
    for k in list(fields) + KEY_PHRASES:
        mm = re.search(r'"%s"\s*:\s*"([^"]*)"' % k, text or "")
        if mm:
            out[k] = mm.group(1)
    return out


def parse(run_dir, passes="A,B,C,D"):
    verdicts = {}
    unparsed = 0
    for tag, (_, fields) in PASSES.items():
        out_path = os.path.join(run_dir, f"output_pass_{tag}.jsonl")
        if not os.path.exists(out_path):
            print(f"[skip] {os.path.basename(out_path)} not found")
            continue
        id_map = json.load(open(os.path.join(run_dir, f"id_map_pass_{tag}.json"),
                                encoding="utf-8"))
        n = 0
        for line in open(out_path, encoding="utf-8"):
            row = json.loads(line)
            meta = id_map.get(row["custom_id"])
            if not meta:
                continue
            body = (row.get("response") or {}).get("body") or {}
            choice = (body.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            v = extract(text, fields)
            if not v or fields[0] not in v:
                unparsed += 1
                continue
            key = (meta["call_id"], meta["judge"])
            verdicts.setdefault(key, {"call_id": meta["call_id"], "judge": meta["judge"]})
            for f in fields:
                if f in v:
                    verdicts[key][f] = v[f]
            for f in KEY_PHRASES:
                if v.get(f):
                    verdicts[key][f] = v[f]
            n += 1
        print(f"pass {tag}: {n} verdicts parsed")

    path = os.path.join(run_dir, "verdicts.jsonl")
    with open(path, "w", encoding="utf-8") as g:
        for key in sorted(verdicts):
            g.write(json.dumps(verdicts[key], ensure_ascii=False) + "\n")
    print(f"\n{len(verdicts)} verdict records -> {path}")
    if unparsed:
        print(f"{unparsed} judge replies could not be parsed. PROTOCOL 5 requires the "
              "unresolved residual to be reported and excluded from denominators.")
    print(f"\nNext: python src/analyze.py --run-id {os.path.basename(run_dir)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--battery", default=BATTERY)
    ap.add_argument("--judges", help="comma-separated; default: two reference judges")
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--passes", default="A,B,C,D",
                    help="Which passes to build or parse. Re-judging one measure "
                         "after a prompt change needs only its own pass; the others "
                         "are unchanged and rebuilding them costs four times as much.")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--parse", action="store_true")
    args = ap.parse_args()

    run_dir = os.path.join(ROOT, "data", "runs", args.run_id)
    if not os.path.isdir(run_dir):
        sys.exit(f"no such run: {run_dir}")
    if args.build and not os.path.exists(os.path.join(run_dir, "responses.jsonl")):
        sys.exit(f"{args.run_id} holds no responses.jsonl. Build batches against a "
                 "collection, not against an analysis directory.")
    if args.build:
        battery = json.load(open(args.battery, encoding="utf-8"))
        judges = args.judges.split(",") if args.judges else DEFAULT_JUDGES
        build(run_dir, battery, judges, args.max_tokens, args.passes)
    elif args.parse:
        parse(run_dir, args.passes)
    else:
        sys.exit("choose --build or --parse")


if __name__ == "__main__":
    main()
