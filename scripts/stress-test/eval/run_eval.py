#!/usr/bin/env python3
"""SCM Chatflow Evaluation Harness — CLI entry point.

Usage:
    python run_eval.py --dataset datasets/scm_eval_v1.jsonl --base-url http://localhost/v1 --api-key app-xxx
    python run_eval.py --dataset datasets/scm_eval_v1.jsonl --sample 5 --judge-mode off
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Allow imports from parent stress-test directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.dify_client import EvalResponse, send_query
from eval.judge_openrouter import JudgeScores, aggregate_judge_scores, judge_case
from eval.scoring import CaseScore, RuleCheckResult, aggregate_scores, score_case

try:
    from common.config_helper import config_helper
except ImportError:
    config_helper = None


def load_dataset(
    path: Path, sample: int | None = None, seed: int = 42
) -> list[dict[str, Any]]:
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if sample and sample < len(cases):
        import random

        rng = random.Random(seed)
        cases = rng.sample(cases, sample)
    return cases


def load_thresholds(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


LANG_PICK_UTTERANCE = {"en": "English", "fr": "Français"}


def _case_lang(case: dict[str, Any]) -> str | None:
    """Return 'en' / 'fr' / None (legacy monolingual case)."""
    raw = str(case.get("lang", "") or "").strip().lower()
    if raw in {"en", "fr"}:
        return raw
    return None


def run_single_case(
    case: dict[str, Any],
    *,
    base_url: str,
    api_key: str,
) -> dict[str, Any]:
    """Run a single eval case and return full result dict.

    If ``case["lang"]`` is ``"en"`` or ``"fr"``, the bilingual workflow is driven via
    a two-turn conversation: first send the language-pick utterance, capture the
    server-assigned conversation_id, then send the real query on the same
    conversation and score only the second turn. Legacy single-turn cases (no
    ``lang`` field) are unchanged.
    """
    lang = _case_lang(case)

    turn1_ack: str | None = None
    turn1_error: str | None = None
    conversation_id = ""

    if lang is not None:
        pick = LANG_PICK_UTTERANCE[lang]
        turn1: EvalResponse = send_query(pick, base_url=base_url, api_key=api_key)
        conversation_id = turn1.conversation_id
        turn1_ack = turn1.final_answer
        turn1_error = turn1.error
        if turn1_error or not conversation_id:
            # Bail out: report as a failed case with a clear reason, skip turn 2.
            empty_scores = score_case(
                case=case,
                final_answer=turn1_ack or "",
                nodes_fired=turn1.nodes_fired,
                citations=turn1.citations,
            )
            return {
                "case_id": case["case_id"],
                "lang": lang,
                "query": case["query"],
                "expected_route": case["expected_route"],
                "final_answer": turn1_ack or "",
                "turn1_ack": turn1_ack,
                "turn1_error": turn1_error,
                "conversation_id": conversation_id,
                "nodes_fired": turn1.nodes_fired,
                "citations_count": len(turn1.citations),
                "citations": turn1.citations,
                "timing": turn1.timing,
                "error": turn1_error or "No conversation_id returned on turn 1",
                "scores": empty_scores.to_dict(),
                "_score_obj": empty_scores,
                "passed": False,
            }

    resp: EvalResponse = send_query(
        case["query"],
        base_url=base_url,
        api_key=api_key,
        conversation_id=conversation_id,
    )

    scores: CaseScore = score_case(
        case=case,
        final_answer=resp.final_answer,
        nodes_fired=resp.nodes_fired,
        citations=resp.citations,
    )

    return {
        "case_id": case["case_id"],
        "lang": lang or "en",
        "query": case["query"],
        "expected_route": case["expected_route"],
        "final_answer": resp.final_answer,
        "turn1_ack": turn1_ack,
        "conversation_id": resp.conversation_id or conversation_id,
        "nodes_fired": resp.nodes_fired,
        "citations_count": len(resp.citations),
        "citations": resp.citations,
        "timing": resp.timing,
        "error": resp.error,
        "scores": scores.to_dict(),
        "_score_obj": scores,
        "passed": scores.passed,
    }


def run_judge(
    results: list[dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
) -> list[JudgeScores]:
    """Run LLM judge on all results.

    Cases that never produced an answer (turn-1 bailout or transport error) are
    short-circuited with a skipped-judge marker so we don't waste OpenRouter
    calls scoring an empty string or let junk scores drag the averages down.
    """
    judge_scores = []
    for r in results:
        if r.get("error") or not (r.get("final_answer") or "").strip():
            js = JudgeScores(error="skipped: no answer to judge")
        else:
            case = cases_by_id[r["case_id"]]
            js = judge_case(
                query=r["query"],
                answer=r["final_answer"],
                reference_answer=case.get("reference_answer", ""),
                citations=r.get("citations", []),
                lang=r.get("lang") or (case.get("lang") or "en"),
            )
        r["judge_scores"] = js.to_dict()
        judge_scores.append(js)
    return judge_scores


def generate_summary_md(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    """Generate a human-readable markdown report."""
    lines = [
        "# SCM Chatflow Evaluation Report",
        "",
        f"**Date**: {summary['timestamp']}",
        f"**Total cases**: {summary['total_cases']}",
        f"**Passed**: {summary['passed']} | **Failed**: {summary['failed']}",
        f"**Pass rate**: {summary['pass_rate']:.1%}",
        f"**Avg score**: {summary['avg_score']:.3f}",
        "",
        "## Per-Check Pass Rates",
        "",
        "| Check | Rate |",
        "|-------|------|",
    ]
    for check, rate in summary.get("per_check", {}).items():
        lines.append(f"| {check} | {rate:.1%} |")

    lines.extend(
        [
            "",
            "## Per-Category Pass Rates",
            "",
            "| Category | Total | Passed | Rate |",
            "|----------|-------|--------|------|",
        ]
    )
    for cat, data in summary.get("per_category", {}).items():
        lines.append(
            f"| {cat} | {data['total']} | {data['passed']} | {data['pass_rate']:.1%} |"
        )

    per_language = summary.get("per_language") or {}
    if per_language:
        lines.extend(
            [
                "",
                "## Per-Language Pass Rates",
                "",
                "| Language | Total | Passed | Rate | Avg Score |",
                "|----------|-------|--------|------|-----------|",
            ]
        )
        for lang, data in per_language.items():
            lines.append(
                f"| {lang} | {data['total']} | {data['passed']} | "
                f"{data['pass_rate']:.1%} | {data.get('avg_score', 0.0):.3f} |"
            )

    if summary.get("judge"):
        lines.extend(
            [
                "",
                "## LLM Judge Scores (averages)",
                "",
                "| Dimension | Score |",
                "|-----------|-------|",
            ]
        )
        for dim in ["correctness", "groundedness", "completeness", "tone"]:
            val = summary["judge"].get(dim)
            lines.append(
                f"| {dim} | {val:.3f}" if val is not None else f"| {dim} | N/A |"
            )

    # Failed cases
    failed = [r for r in results if not r["passed"]]
    if failed:
        lines.extend(
            [
                "",
                f"## Failed Cases ({len(failed)})",
                "",
            ]
        )
        for r in failed:
            checks = r["scores"].get("rule_checks", [])
            failed_checks = [c["name"] for c in checks if not c["passed"]]
            lines.append(
                f"- **{r['case_id']}**: `{r['query'][:80]}` — failed: {', '.join(failed_checks)}"
            )

    if summary.get("threshold_breaches"):
        lines.extend(
            [
                "",
                "## Threshold Breaches",
                "",
            ]
        )
        for breach in summary["threshold_breaches"]:
            lines.append(
                f"- **{breach['metric']}**: {breach['actual']:.3f} < {breach['threshold']:.3f}"
            )

    lines.append("")
    return "\n".join(lines)


def check_thresholds(
    summary: dict[str, Any],
    thresholds: dict[str, Any],
    judge_summary: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Check summary metrics against thresholds. Returns list of breaches."""
    breaches = []
    g = thresholds.get("global", {})

    if "pass_rate" in g and summary["pass_rate"] < g["pass_rate"]:
        breaches.append(
            {
                "metric": "global.pass_rate",
                "actual": summary["pass_rate"],
                "threshold": g["pass_rate"],
            }
        )

    route_rate = summary.get("per_check", {}).get("route_correctness", 1.0)
    if "route_accuracy" in g and route_rate < g["route_accuracy"]:
        breaches.append(
            {
                "metric": "global.route_accuracy",
                "actual": route_rate,
                "threshold": g["route_accuracy"],
            }
        )

    citation_rate = summary.get("per_check", {}).get("citation_check", 1.0)
    if "citation_coverage" in g and citation_rate < g["citation_coverage"]:
        breaches.append(
            {
                "metric": "global.citation_coverage",
                "actual": citation_rate,
                "threshold": g["citation_coverage"],
            }
        )

    compliance_rate = summary.get("per_check", {}).get("compliance", 1.0)
    if "compliance_rate" in g and compliance_rate < g["compliance_rate"]:
        breaches.append(
            {
                "metric": "global.compliance_rate",
                "actual": compliance_rate,
                "threshold": g["compliance_rate"],
            }
        )

    lang_lock_rate = summary.get("per_check", {}).get("language_lock_taken")
    if (
        "language_lock_rate" in g
        and lang_lock_rate is not None
        and lang_lock_rate < g["language_lock_rate"]
    ):
        breaches.append(
            {
                "metric": "global.language_lock_rate",
                "actual": lang_lock_rate,
                "threshold": g["language_lock_rate"],
            }
        )

    per_language_thresholds = thresholds.get("per_language", {}) or {}
    per_language_summary = summary.get("per_language", {}) or {}
    for lang, rules in per_language_thresholds.items():
        bucket = per_language_summary.get(lang)
        if not bucket:
            continue
        target = rules.get("pass_rate")
        if target is not None and bucket.get("pass_rate", 0.0) < target:
            breaches.append(
                {
                    "metric": f"per_language.{lang}.pass_rate",
                    "actual": bucket.get("pass_rate", 0.0),
                    "threshold": target,
                }
            )

    if judge_summary:
        for dim, target in (thresholds.get("judge") or {}).items():
            val = judge_summary.get(dim)
            if val is not None and val < target:
                breaches.append(
                    {
                        "metric": f"judge.{dim}",
                        "actual": val,
                        "threshold": target,
                    }
                )

    return breaches


def main() -> int:
    parser = argparse.ArgumentParser(description="SCM Chatflow Evaluation Harness")
    parser.add_argument(
        "--dataset", type=Path, required=True, help="Path to JSONL dataset"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost/v1",
        help="Dify service API base URL",
    )
    parser.add_argument(
        "--app-id", type=str, default=None, help="App ID (unused, for future use)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="App API key (app-xxx). Falls back to config_helper.",
    )
    parser.add_argument(
        "--sample", type=int, default=None, help="Run only N random cases"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    parser.add_argument(
        "--judge-mode",
        choices=["openrouter", "off"],
        default="off",
        help="LLM judge mode",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        default=Path(__file__).parent / "config" / "thresholds.yml",
    )
    parser.add_argument(
        "--fail-on-thresholds",
        action="store_true",
        help="Exit 1 if any threshold breached",
    )
    parser.add_argument(
        "--language-filter",
        choices=["en", "fr", "both"],
        default="both",
        help="Only run cases of this language (cases without a lang field are treated as 'en').",
    )
    args = parser.parse_args()

    # Resolve API key
    api_key = args.api_key
    if not api_key and config_helper:
        api_key = config_helper.get_api_key()
    if not api_key:
        print("ERROR: No API key provided. Use --api-key or run setup scripts first.")
        return 1

    # Load dataset
    cases = load_dataset(args.dataset, sample=args.sample, seed=args.seed)
    if args.language_filter != "both":
        before = len(cases)
        cases = [c for c in cases if (_case_lang(c) or "en") == args.language_filter]
        print(
            f"Filtered by language={args.language_filter}: {before} -> {len(cases)} cases"
        )
    print(f"Loaded {len(cases)} eval cases from {args.dataset}")
    if args.sample:
        print(f"  (sampled {args.sample} with seed={args.seed})")

    # Load thresholds
    thresholds = load_thresholds(args.thresholds) if args.thresholds.exists() else {}

    # Preflight check: send one request to verify auth works
    print("Preflight auth check...", end="", flush=True)
    preflight = send_query("hello", base_url=args.base_url, api_key=api_key)
    if preflight.error and (
        "401" in preflight.error or "unauthorized" in preflight.error.lower()
    ):
        print(f" FAILED\nERROR: API key is invalid or expired: {preflight.error}")
        print(
            "Get a valid key from Dify > Your App > API Access, then pass it via --api-key"
        )
        return 1
    if preflight.error and (
        "connection" in preflight.error.lower() or "connect" in preflight.error.lower()
    ):
        print(f" FAILED\nERROR: Cannot connect to {args.base_url}: {preflight.error}")
        return 1
    print(" OK")

    # Run cases
    results: list[dict[str, Any]] = []
    cases_by_id = {c["case_id"]: c for c in cases}
    consecutive_errors = 0
    t_start = time.monotonic()

    for i, case in enumerate(cases, 1):
        lang_tag = f"[{_case_lang(case) or 'en'}]"
        print(
            f"  [{i}/{len(cases)}] {lang_tag} {case['case_id']}: {case['query'][:60]}...",
            end="",
            flush=True,
        )
        result = run_single_case(case, base_url=args.base_url, api_key=api_key)
        status = "PASS" if result["passed"] else "FAIL"
        elapsed = result["timing"].get("total_seconds", 0)

        if result["error"]:
            consecutive_errors += 1
            print(f" ERROR ({result['error'][:80]})")
            if consecutive_errors >= 3:
                print(
                    f"\nABORTED: {consecutive_errors} consecutive errors. Fix the issue and retry."
                )
                return 1
        else:
            consecutive_errors = 0
            print(f" {status} ({elapsed:.1f}s)")

        results.append(result)

    t_total = time.monotonic() - t_start

    # Optional judge
    judge_summary = None
    if args.judge_mode == "openrouter":
        print("\nRunning LLM judge...")
        judge_scores = run_judge(results, cases_by_id)
        judge_summary = aggregate_judge_scores(judge_scores)

    # Aggregate scores using the CaseScore objects attached by run_single_case;
    # optionally fold judge-threshold failures into the per-case rule_checks so
    # the pass/fail verdict and aggregation agree.
    judge_thresholds = thresholds.get("judge") or {}
    score_objects: list[CaseScore] = []
    for r in results:
        s = r["_score_obj"]
        if args.judge_mode == "openrouter" and judge_thresholds:
            js = r.get("judge_scores") or {}
            failed_dims = [
                f"{dim}={js[dim]:.2f}<{min_val}"
                for dim, min_val in judge_thresholds.items()
                if js.get(dim) is not None and js[dim] < min_val
            ]
            if failed_dims:
                detail = "; ".join(failed_dims)
                s.rule_checks.append(
                    RuleCheckResult(
                        name="judge_thresholds",
                        passed=False,
                        detail=detail,
                    )
                )
                s.passed = False
                r["passed"] = False
                r["scores"]["passed"] = False
                r["scores"]["rule_checks"].append(
                    {
                        "name": "judge_thresholds",
                        "passed": False,
                        "detail": detail,
                    }
                )
        score_objects.append(s)

    agg = aggregate_scores(score_objects)

    # Check thresholds (include judge averages)
    breaches = check_thresholds(agg, thresholds, judge_summary=judge_summary)

    # Build summary
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    summary = {
        "timestamp": timestamp,
        "total_seconds": round(t_total, 1),
        **agg,
        "judge": judge_summary,
        "threshold_breaches": breaches,
    }

    # Write outputs
    out_dir = args.output_dir / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "cases.jsonl", "w") as f:
        for r in results:
            serializable = {k: v for k, v in r.items() if not k.startswith("_")}
            f.write(json.dumps(serializable, default=str) + "\n")

    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    md_report = generate_summary_md(summary, results)
    with open(out_dir / "summary.md", "w") as f:
        f.write(md_report)

    # Print summary
    print(f"\n{'=' * 60}")
    print(
        f"EVALUATION COMPLETE — {summary['total_cases']} cases in {summary['total_seconds']}s"
    )
    print(f"{'=' * 60}")
    print(
        f"Pass rate:  {summary['pass_rate']:.1%} ({summary['passed']}/{summary['total_cases']})"
    )
    print(f"Avg score:  {summary['avg_score']:.3f}")
    print()
    print("Per-check pass rates:")
    for check, rate in summary.get("per_check", {}).items():
        print(f"  {check:25s} {rate:.1%}")
    print()
    print("Per-category pass rates:")
    for cat, data in summary.get("per_category", {}).items():
        print(f"  {cat:15s} {data['pass_rate']:.1%} ({data['passed']}/{data['total']})")

    per_language_block = summary.get("per_language") or {}
    if per_language_block:
        print()
        print("Per-language pass rates:")
        for lang, data in per_language_block.items():
            print(
                f"  {lang:15s} {data['pass_rate']:.1%} "
                f"({data['passed']}/{data['total']}) avg_score={data.get('avg_score', 0.0):.3f}"
            )

    lang_lock_rate = summary.get("per_check", {}).get("language_lock_taken")
    if lang_lock_rate is not None:
        print()
        print(f"Language-lock rate: {lang_lock_rate:.1%}")

    if judge_summary:
        print()
        judged = judge_summary.get("judged_count", 0)
        errors = judge_summary.get("judge_errors", 0)
        total = judged + errors
        print(f"LLM Judge averages ({judged}/{total} cases scored, {errors} errors):")
        for dim in ["correctness", "groundedness", "completeness", "tone"]:
            val = judge_summary.get(dim)
            print(f"  {dim:15s} {val:.3f}" if val is not None else f"  {dim:15s} N/A")

    if breaches:
        print()
        print("THRESHOLD BREACHES:")
        for b in breaches:
            print(f"  {b['metric']}: {b['actual']:.3f} < {b['threshold']:.3f}")

    print(f"\nResults written to: {out_dir}")

    if args.fail_on_thresholds and breaches:
        print("\nFAILED: Threshold breaches detected.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
