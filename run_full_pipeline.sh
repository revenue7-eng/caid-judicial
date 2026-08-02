#!/bin/bash
# Full CAID-J pipeline.
#
# Modes:
#   --smoke            1 model, 1 case, 1 replicate. Sanity check, a few calls.
#   --resume <RUN_ID>  continue an interrupted collection.
#   (default)          full factorial as declared in prompts/judicial_v1.json
#
# Required:
#   OPENROUTER_API_KEY      for response collection
#
# The judge passes run on a batch-capable OpenAI-compatible endpoint. This
# script builds the four batch files and stops; upload them, save the results
# as output_pass_A.jsonl ... output_pass_D.jsonl in the same run directory,
# then re-run with --parse to finish.

set -e
cd "$(dirname "$0")"

N=3
SMOKE=0
EXTRA=""
RUN_ID=""
MODE="collect"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke)  EXTRA="$EXTRA --smoke"; N=1; SMOKE=1; shift ;;
    --resume) RUN_ID="$2"; EXTRA="$EXTRA --resume"; shift 2 ;;
    --parse)  RUN_ID="$2"; MODE="parse"; shift 2 ;;
    --n)      N="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ -z "$RUN_ID" ]]; then
  RUN_ID=$(date -u +"%Y%m%d_%H%M%S")
fi

echo "=========================================="
echo "CAID-J pipeline"
echo "Run ID: $RUN_ID"
if [[ "$SMOKE" == "1" ]]; then echo "Mode: smoke (1 model, 1 case, 1 replicate)"; else echo "Replicates: $N"; fi
echo "=========================================="

if [[ "$MODE" == "collect" ]]; then
  echo ""
  echo ">>> Step 1: collect responses"
  python3 src/run_benchmark.py --run-id "$RUN_ID" --n "$N" $EXTRA

  echo ""
  echo ">>> Step 2: build judge batches (four single-question passes, two judges)"
  python3 src/judge_batch.py --run-id "$RUN_ID" --build

  echo ""
  echo "=========================================="
  echo "Upload these four files to your batch endpoint:"
  echo "  data/runs/$RUN_ID/batch_pass_[ABCD].jsonl"
  echo "Save the results alongside them as output_pass_[ABCD].jsonl, then:"
  echo "  ./run_full_pipeline.sh --parse $RUN_ID"
  echo "=========================================="
else
  echo ""
  echo ">>> Step 3: parse verdicts"
  python3 src/judge_batch.py --run-id "$RUN_ID" --parse

  echo ""
  echo ">>> Step 4: metrics, pair-level significance, judge agreement"
  python3 src/analyze.py --run-id "$RUN_ID"

  echo ""
  echo "=========================================="
  echo "Complete. Output: data/runs/$RUN_ID/"
  echo "=========================================="
fi
