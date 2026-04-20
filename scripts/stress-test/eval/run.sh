#!/usr/bin/env bash
# Preset eval runners for the SCM bilingual chatflow.
#
# Usage:
#   ./scripts/stress-test/eval/run.sh <preset>
#


# Presets:
#   smoke          5-sample bilingual sanity test (no judge)          ~2 min
#   en             10 English-only cases                              ~4 min
#   fr             10 French-only cases                               ~4 min
#   full           Full 244-case bilingual eval (no judge)            ~90 min
#   judge          Full eval + LLM judge + fail-on-threshold          ~120 min
#   smoke-judge    5-sample + LLM judge                               ~3 min
#   category <N>   N samples filtered in post (trading/deposits/etc.) varies
#
# Keys (override with env vars if needed):
#   DIFY_APP_KEY           Dify app API key       (default: the known Broker_test app)
#   OPENROUTER_API_KEY     OpenRouter judge key   (default: the known key)

set -euo pipefail

# Always run from repo root so relative paths resolve consistently.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
cd "$REPO_ROOT"

DATASET_BILINGUAL="scripts/stress-test/eval/datasets/scm_eval_bilingual_v1.jsonl"
DATASET_EN_LEGACY="scripts/stress-test/eval/datasets/scm_eval_v1.jsonl"
DATASET_FR_LEGACY="scripts/stress-test/eval/datasets/scm_eval_v1_fr.jsonl"

API_KEY="${DIFY_APP_KEY:-app-6PQnt9ZS4kB2ch2fYIJd8zwA}"
OR_KEY="${OPENROUTER_API_KEY:-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}"

RUN_EVAL="python scripts/stress-test/eval/run_eval.py"

usage() {
    sed -n '2,18p' "$0"
    exit 1
}

preset="${1:-}"
case "$preset" in
    smoke)
        $RUN_EVAL \
            --dataset "$DATASET_BILINGUAL" \
            --api-key "$API_KEY" \
            --sample 5
        ;;

    en)
        $RUN_EVAL \
            --dataset "$DATASET_BILINGUAL" \
            --api-key "$API_KEY" \
            --language-filter en \
            --sample 10
        ;;

    fr)
        $RUN_EVAL \
            --dataset "$DATASET_BILINGUAL" \
            --api-key "$API_KEY" \
            --language-filter fr \
            --sample 10
        ;;

    full)
        $RUN_EVAL \
            --dataset "$DATASET_BILINGUAL" \
            --api-key "$API_KEY"
        ;;

    judge)
        OPENROUTER_API_KEY="$OR_KEY" $RUN_EVAL \
            --dataset "$DATASET_BILINGUAL" \
            --api-key "$API_KEY" \
            --judge-mode openrouter \
            --fail-on-thresholds
        ;;

    smoke-judge)
        OPENROUTER_API_KEY="$OR_KEY" $RUN_EVAL \
            --dataset "$DATASET_BILINGUAL" \
            --api-key "$API_KEY" \
            --sample 5 \
            --judge-mode openrouter
        ;;

    category)
        # ./run.sh category <sample-count>  — sampled run with deterministic seed
        # so you can rerun the exact same slice after a fix.
        n="${2:-20}"
        $RUN_EVAL \
            --dataset "$DATASET_BILINGUAL" \
            --api-key "$API_KEY" \
            --sample "$n" \
            --seed 42
        ;;

    legacy-en)
        # Old monolingual English dataset — will fail against the bilingual app
        # because cases have no `lang` field. Kept for reference/regression only.
        $RUN_EVAL \
            --dataset "$DATASET_EN_LEGACY" \
            --api-key "$API_KEY" \
            --sample 5
        ;;

    legacy-fr)
        $RUN_EVAL \
            --dataset "$DATASET_FR_LEGACY" \
            --api-key "$API_KEY" \
            --sample 5
        ;;

    "" | -h | --help)
        usage
        ;;

    *)
        echo "Unknown preset: $preset" >&2
        usage
        ;;
esac
