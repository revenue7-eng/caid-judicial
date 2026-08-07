#!/usr/bin/env python3
"""
CAID-J judge, one call at a time, against any OpenAI-compatible endpoint.

Same passes, same prompts and same verdict records as judge_batch.py. The batch
path is cheaper on a large corpus; this one needs nothing but a chat completions
endpoint, so a re-judge does not depend on any single provider having credit.

    python src/judge_run.py --run-id run_base_96 --passes B,D

Judges and where they live are given per judge, because the two reference models
are rarely hosted by the same provider:

    --judge "Qwen/Qwen3.5-397B-A17B-FP8=https://api.novita.ai/openai:NOVITA_API_KEY"
    --judge "deepseek-v4-pro=https://api.deepseek.com/v1:DEEPSEEK_API_KEY"

Without --judge it falls back to JUDGE_BASE_URL and JUDGE_KEY_ENV for the two
reference judges, which suits a provider that hosts both.

Interrupted runs continue with --resume: verdicts already written are skipped.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from judge_batch import PASSES, KEY_PHRASES, DEFAULT_JUDGES, BATTERY, ROOT, fill, extract


def parse_judge_spec(spec):
    """model=base_url:KEY_ENV -> (model, base_url, key_env)."""
    if "=" not in spec:
        sys.exit(f"--judge needs model=base_url:KEY_ENV, got: {spec}")
    model, rest = spec.split("=", 1)
    if ":" not in rest.rsplit("/", 1)[-1]:
        sys.exit(f"--judge is missing :KEY_ENV, got: {spec}")
    base_url, key_env = rest.rsplit(":", 1)
    return model.strip(), base_url.strip(), key_env.strip()


def call(session, base_url, model, api_key, content, max_tokens, timeout):
    r = session.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"model": model,
              "messages": [{"role": "user", "content": content}],
              "temperature": 0.0,
              "max_tokens": max_tokens},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--battery", default=BATTERY)
    ap.add_argument("--passes", default="A,B,C,D")
    ap.add_argument("--judge", action="append", default=[],
                    help="model=base_url:KEY_ENV, repeatable")
    ap.add_argument("--base-url", default=os.environ.get("JUDGE_BASE_URL"))
    ap.add_argument("--api-key-env", default=os.environ.get("JUDGE_KEY_ENV", "JUDGE_API_KEY"))
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--pace", type=float, default=0.2, help="seconds between calls")
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    if args.judge:
        judges = [parse_judge_spec(s) for s in args.judge]
    else:
        if not args.base_url:
            sys.exit("Give --judge per judge, or set JUDGE_BASE_URL for both.")
        judges = [(m, args.base_url, args.api_key_env) for m in DEFAULT_JUDGES]

    for model, _, key_env in judges:
        if not os.environ.get(key_env):
            sys.exit(f"{key_env} is not set (needed for {model})")

    run_dir = os.path.join(ROOT, "data", "runs", args.run_id)
    battery = json.load(open(args.battery, encoding="utf-8"))
    combos = {c["id"]: c for c in battery["combos"]}

    responses = [json.loads(l) for l in
                 open(os.path.join(run_dir, "responses.jsonl"), encoding="utf-8")]
    responses = [r for r in responses if (r.get("response") or "").strip()]

    tested = set(battery.get("reference_models", [])) | {r["model"] for r in responses}
    for model, _, _ in judges:
        if model in tested:
            sys.exit(f"REFUSING TO RUN: judge {model} is one of the models under test.\n"
                     "PROTOCOL 5: a judge scoring itself makes any result in its favour "
                     "worthless.")

    wanted = {t.strip().upper() for t in args.passes.split(",") if t.strip()}
    unknown = wanted - set(PASSES)
    if unknown:
        sys.exit(f"Unknown pass: {', '.join(sorted(unknown))}")

    # Existing verdicts are kept and merged, so one pass can be redone without
    # discarding the others.
    verdicts = {}
    vpath = os.path.join(run_dir, "verdicts.jsonl")
    if os.path.exists(vpath):
        for line in open(vpath, encoding="utf-8"):
            v = json.loads(line)
            verdicts[(v["call_id"], v["judge"])] = v

    session = requests.Session()
    total_ok = total_fail = 0

    for tag in sorted(wanted):
        prompt_file, fields = PASSES[tag]
        template = open(os.path.join(ROOT, "prompts", prompt_file),
                        encoding="utf-8").read()
        jobs = [(r, model, base, key) for model, base, key in judges for r in responses]
        if args.resume:
            jobs = [(r, m, b, k) for r, m, b, k in jobs
                    if fields[0] not in verdicts.get((r["call_id"], m), {})]
        if args.limit:
            jobs = jobs[: args.limit]
        if not jobs:
            print(f"pass {tag}: nothing to do")
            continue

        print(f"pass {tag}: {len(jobs)} calls, prompt {prompt_file}")
        n_ok = n_fail = 0
        for i, (r, model, base, key_env) in enumerate(jobs, 1):
            content = fill(template, battery, combos[r["case"]], r["response"])
            body = None
            for attempt in range(args.retries):
                try:
                    body = call(session, base, model, os.environ[key_env],
                                content, args.max_tokens, args.timeout)
                    break
                except Exception as e:
                    if attempt == args.retries - 1:
                        print(f"  [fail] {r['call_id']} / {model}: {e}")
                    else:
                        time.sleep(2 ** attempt)

            v = None
            if body is not None:
                choice = (body.get("choices") or [{}])[0]
                text = (choice.get("message") or {}).get("content") or ""
                v = extract(text, fields)

            if not v or fields[0] not in v:
                n_fail += 1
            else:
                key = (r["call_id"], model)
                verdicts.setdefault(key, {"call_id": r["call_id"], "judge": model})
                for f in fields:
                    if f in v:
                        verdicts[key][f] = v[f]
                for f in KEY_PHRASES:
                    if v.get(f):
                        verdicts[key][f] = v[f]
                n_ok += 1

            if i % 25 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)}  ok={n_ok} unparsed={n_fail}")
                with open(vpath, "w", encoding="utf-8") as g:
                    for k in sorted(verdicts):
                        g.write(json.dumps(verdicts[k], ensure_ascii=False) + "\n")
            if args.pace:
                time.sleep(args.pace)

        total_ok += n_ok
        total_fail += n_fail

    with open(vpath, "w", encoding="utf-8") as g:
        for k in sorted(verdicts):
            g.write(json.dumps(verdicts[k], ensure_ascii=False) + "\n")

    print(f"\n{len(verdicts)} verdict records -> {vpath}")
    if total_fail:
        print(f"{total_fail} judge replies could not be parsed. PROTOCOL 5 requires the "
              "unresolved residual to be reported and excluded from denominators.")
    print(f"\nNext: python src/analyze.py --run-id {args.run_id}")


if __name__ == "__main__":
    main()
