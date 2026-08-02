#!/usr/bin/env python3
"""
CAID-J benchmark runner: response collection.

Full factorial: all combos x all conditions x N replicates x all models.

    export OPENROUTER_API_KEY="..."
    python src/run_benchmark.py --run-id my_run --n 3
    python src/run_benchmark.py --run-id my_run --n 3 --resume
    python src/run_benchmark.py --run-id my_run --smoke

Writes data/runs/<run-id>/responses.jsonl and run_config.json.

Resume skips any (case, condition, model, replicate) already present with a
non-empty response. Rows present but empty are re-issued: a provider that
returned nothing once should not be recorded as done forever.

Standard library only.
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATTERY = os.path.join(ROOT, "prompts", "judicial_v1.json")
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def load_battery(path):
    b = json.load(open(path, encoding="utf-8"))
    for combo in b["combos"]:
        if not combo.get("defence_at_issue"):
            sys.exit(f"battery combo {combo['id']} has no defence_at_issue (PROTOCOL 3)")
    if "{case}" not in b["user_task"]:
        sys.exit("battery user_task must contain the {case} placeholder")
    return b


def call(api_key, model, system_prompt, user_prompt, temperature, max_tokens):
    body = json.dumps({
        "model": model, "temperature": temperature, "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": user_prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/revenue7-eng/caid-judicial",
                 "X-Title": "CAID-J benchmark"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        status = resp.status
        data = json.loads(resp.read().decode("utf-8"))
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    text = msg.get("content") or ""          # never .strip() a None
    used_reasoning = False
    if not text:
        # Some reasoning models leave content empty and put everything in a
        # separate field. Falling back keeps the row non-blank, but the row is
        # deliberation rather than an answer, so PROTOCOL 4 requires a flag.
        text = msg.get("reasoning") or ""
        used_reasoning = bool(text)
    return text.strip(), {
        "http_status": status,
        "finish_reason": choice.get("finish_reason"),
        "usage": data.get("usage"),
        "used_reasoning": used_reasoning,
        "response_id": data.get("id"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--battery", default=BATTERY)
    ap.add_argument("--models", help="comma-separated; default: battery reference_models")
    ap.add_argument("--conditions", help="comma-separated; default: all in battery")
    ap.add_argument("--n", type=int, default=3, help="replicates per cell")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--pace-min", type=float, default=3.0)
    ap.add_argument("--pace-max", type=float, default=5.0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="1 model, 1 case, n=1")
    args = ap.parse_args()

    battery = load_battery(args.battery)
    models = (args.models.split(",") if args.models else battery["reference_models"])
    conditions = (args.conditions.split(",") if args.conditions
                  else list(battery["system_prompts"]))
    combos = battery["combos"]
    n = args.n

    if args.smoke:
        models, combos, n = models[:1], combos[:1], 1
        print("[smoke] 1 model, 1 case, 1 replicate")

    if args.temperature <= 0 and n > 1:
        sys.exit("PROTOCOL 3: temperature must be above zero when replicates > 1, "
                 "otherwise the replicates are copies.")
    if len([c for c in conditions if c != "neutral"]) < 3:
        print("[note] fewer than three configured wordings. PROTOCOL 2a: the report must "
              "state that the result is a property of the wordings tested.")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY in your environment first.")

    out_dir = os.path.join(ROOT, "data", "runs", args.run_id)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "responses.jsonl")

    done = set()
    if args.resume and os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if (r.get("response") or "").strip():
                done.add(r["call_id"])
        print(f"[resume] {len(done)} non-empty answers already on disk")
        # rewrite without the empty rows so they get re-issued
        kept = [l for l in open(path, encoding="utf-8")
                if (json.loads(l).get("response") or "").strip()]
        open(path, "w", encoding="utf-8").writelines(kept)

    json.dump({
        "run_id": args.run_id,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "battery_version": battery["version"],
        "models": models, "conditions": conditions,
        "replicates": n, "temperature": args.temperature,
        "max_tokens": args.max_tokens, "endpoint": ENDPOINT,
    }, open(os.path.join(out_dir, "run_config.json"), "w", encoding="utf-8"), indent=2)

    total = len(combos) * len(conditions) * len(models) * n
    issued = 0
    failures = {}

    with open(path, "a", encoding="utf-8") as out:
        for combo in combos:
            user_prompt = battery["user_task"].format(case=combo["case_file"])
            for cond in conditions:
                system_prompt = battery["system_prompts"][cond]
                for model in models:
                    for rep in range(1, n + 1):
                        issued += 1
                        call_id = f"{combo['id']}__{model}__{cond}__r{rep}"
                        tag = f"[{issued}/{total}] {call_id}"
                        if call_id in done:
                            continue
                        try:
                            text, meta = call(api_key, model, system_prompt, user_prompt,
                                              args.temperature, args.max_tokens)
                            err = None
                            note = " (reasoning fallback)" if meta["used_reasoning"] else ""
                            print(f"{tag} ok, {len(text)} chars, "
                                  f"finish={meta['finish_reason']}{note}")
                        except Exception as e:
                            text, meta, err = "", {}, f"{type(e).__name__}: {e}"
                            failures[model] = failures.get(model, 0) + 1
                            print(f"{tag} FAIL {err}")
                        out.write(json.dumps({
                            "call_id": call_id, "run_id": args.run_id,
                            "case": combo["id"], "condition": cond,
                            "model": model, "replicate": rep,
                            "response": text, "error": err, **meta,
                        }, ensure_ascii=False) + "\n")
                        out.flush()
                        time.sleep(random.uniform(args.pace_min, args.pace_max))

    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    empty = sum(1 for r in rows if not (r.get("response") or "").strip())
    print(f"\n{len(rows)}/{total} answers on disk, {empty} empty, "
          f"{sum(failures.values())} failures this pass")
    for m, c in failures.items():
        print(f"  {m}: {c}")
    if failures:
        print("  Confirm the current identifier for the SAME model and run again with "
              "--resume. Never substitute a different model: the design rests on one roster.")
    print(f"\nNext: python src/judge_batch.py --run-id {args.run_id} --build")


if __name__ == "__main__":
    main()
