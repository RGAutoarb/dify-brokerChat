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
from eval.scoring import CaseScore, aggregate_scores, score_case

try:
    from common.config_helper import config_helper
except ImportError:
    config_helper = None


def load_dataset(path: Path, sample: int | None = None, seed: int = 42) -> list[dict[str, Any]]:
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


def run_single_case(
    case: dict[str, Any],
    *,
    base_url: str,
    api_key: str,
) -> dict[str, Any]:
    """Run a single eval case and return full result dict."""
    resp: EvalResponse = send_query(case["query"], base_url=base_url, api_key=api_key)

    scores: CaseScore = score_case(
        case=case,
        final_answer=resp.final_answer,
        nodes_fired=resp.nodes_fired,
        citations=resp.citations,
    )

    return {
        "case_id": case["case_id"],
        "query": case["query"],
        "expected_route": case["expected_route"],
        "final_answer": resp.final_answer,
        "nodes_fired": resp.nodes_fired,
        "citations_count": len(resp.citations),
        "citations": resp.citations,
        "timing": resp.timing,
        "error": resp.error,
        "scores": scores.to_dict(),
        "passed": scores.passed,
    }


def run_judge(
    results: list[dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
) -> list[JudgeScores]:
    """Run LLM judge on all results."""
    judge_scores = []
    for r in results:
        case = cases_by_id[r["case_id"]]
        js = judge_case(
            query=r["query"],
            answer=r["final_answer"],
            reference_answer=case.get("reference_answer", ""),
            citations=r.get("citations", []),
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

    lines.extend([
        "",
        "## Per-Category Pass Rates",
        "",
        "| Category | Total | Passed | Rate |",
        "|----------|-------|--------|------|",
    ])
    for cat, data in summary.get("per_category", {}).items():
        lines.append(f"| {cat} | {data['total']} | {data['passed']} | {data['pass_rate']:.1%} |")

    if summary.get("judge"):
        lines.extend([
            "",
            "## LLM Judge Scores (averages)",
            "",
            "| Dimension | Score |",
            "|-----------|-------|",
        ])
        for dim in ["correctness", "groundedness", "completeness", "tone"]:
            val = summary["judge"].get(dim)
            lines.append(f"| {dim} | {val:.3f}" if val is not None else f"| {dim} | N/A |")

    # Failed cases
    failed = [r for r in results if not r["passed"]]
    if failed:
        lines.extend([
            "",
            f"## Failed Cases ({len(failed)})",
            "",
        ])
        for r in failed:
            checks = r["scores"].get("rule_checks", [])
            failed_checks = [c["name"] for c in checks if not c["passed"]]
            lines.append(f"- **{r['case_id']}**: `{r['query'][:80]}` — failed: {', '.join(failed_checks)}")

    if summary.get("threshold_breaches"):
        lines.extend([
            "",
            "## Threshold Breaches",
            "",
        ])
        for breach in summary["threshold_breaches"]:
            lines.append(f"- **{breach['metric']}**: {breach['actual']:.3f} < {breach['threshold']:.3f}")

    lines.append("")
    return "\n".join(lines)


def check_thresholds(summary: dict[str, Any], thresholds: dict[str, Any]) -> list[dict[str, Any]]:
    """Check summary metrics against thresholds. Returns list of breaches."""
    breaches = []
    g = thresholds.get("global", {})

    if "pass_rate" in g and summary["pass_rate"] < g["pass_rate"]:
        breaches.append({"metric": "global.pass_rate", "actual": summary["pass_rate"], "threshold": g["pass_rate"]})

    route_rate = summary.get("per_check", {}).get("route_correctness", 1.0)
    if "route_accuracy" in g and route_rate < g["route_accuracy"]:
        breaches.append({"metric": "global.route_accuracy", "actual": route_rate, "threshold": g["route_accuracy"]})

    citation_rate = summary.get("per_check", {}).get("citation_check", 1.0)
    if "citation_coverage" in g and citation_rate < g["citation_coverage"]:
        breaches.append({"metric": "global.citation_coverage", "actual": citation_rate, "threshold": g["citation_coverage"]})

    compliance_rate = summary.get("per_check", {}).get("compliance", 1.0)
    if "compliance_rate" in g and compliance_rate < g["compliance_rate"]:
        breaches.append({"metric": "global.compliance_rate", "actual": compliance_rate, "threshold": g["compliance_rate"]})

    return breaches


def main() -> int:
    parser = argparse.ArgumentParser(description="SCM Chatflow Evaluation Harness")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to JSONL dataset")
    parser.add_argument("--base-url", type=str, default="http://localhost/v1", help="Dify service API base URL")
    parser.add_argument("--app-id", type=str, default=None, help="App ID (unused, for future use)")
    parser.add_argument("--api-key", type=str, default=None, help="App API key (app-xxx). Falls back to config_helper.")
    parser.add_argument("--sample", type=int, default=None, help="Run only N random cases")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    parser.add_argument("--judge-mode", choices=["openrouter", "off"], default="off", help="LLM judge mode")
    parser.add_argument("--output-dir", type=Path, default=Path("results"), help="Output directory for results")
    parser.add_argument("--thresholds", type=Path, default=Path(__file__).parent / "config" / "thresholds.yml")
    parser.add_argument("--fail-on-thresholds", action="store_true", help="Exit 1 if any threshold breached")
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
    print(f"Loaded {len(cases)} eval cases from {args.dataset}")
    if args.sample:
        print(f"  (sampled {args.sample} with seed={args.seed})")

    # Load thresholds
    thresholds = load_thresholds(args.thresholds) if args.thresholds.exists() else {}

    # Preflight check: send one request to verify auth works
    print("Preflight auth check...", end="", flush=True)
    preflight = send_query("hello", base_url=args.base_url, api_key=api_key)
    if preflight.error and ("401" in preflight.error or "unauthorized" in preflight.error.lower()):
        print(f" FAILED\nERROR: API key is invalid or expired: {preflight.error}")
        print("Get a valid key from Dify > Your App > API Access, then pass it via --api-key")
        return 1
    if preflight.error and ("connection" in preflight.error.lower() or "connect" in preflight.error.lower()):
        print(f" FAILED\nERROR: Cannot connect to {args.base_url}: {preflight.error}")
        return 1
    print(" OK")

    # Run cases
    results: list[dict[str, Any]] = []
    cases_by_id = {c["case_id"]: c for c in cases}
    consecutive_errors = 0
    t_start = time.monotonic()

    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case['case_id']}: {case['query'][:60]}...", end="", flush=True)
        result = run_single_case(case, base_url=args.base_url, api_key=api_key)
        status = "PASS" if result["passed"] else "FAIL"
        elapsed = result["timing"].get("total_seconds", 0)

        if result["error"]:
            consecutive_errors += 1
            print(f" ERROR ({result['error'][:80]})")
            if consecutive_errors >= 3:
                print(f"\nABORTED: {consecutive_errors} consecutive errors. Fix the issue and retry.")
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

    # Aggregate scores
    all_scores = [CaseScore(**{
        "case_id": r["scores"]["case_id"],
        "total_score": r["scores"]["total_score"],
        "passed": r["scores"]["passed"],
    }) for r in results]
    # Re-score properly for aggregation
    score_objects = []
    for r in results:
        case = cases_by_id[r["case_id"]]
        s = score_case(case, r["final_answer"], r["nodes_fired"], r.get("citations", []))
        score_objects.append(s)

    agg = aggregate_scores(score_objects)

    # Check thresholds
    breaches = check_thresholds(agg, thresholds)

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
            f.write(json.dumps(r, default=str) + "\n")

    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    md_report = generate_summary_md(summary, results)
    with open(out_dir / "summary.md", "w") as f:
        f.write(md_report)

    # Print summary
    print(f"\n{'='*60}")
    print(f"EVALUATION COMPLETE — {summary['total_cases']} cases in {summary['total_seconds']}s")
    print(f"{'='*60}")
    print(f"Pass rate:  {summary['pass_rate']:.1%} ({summary['passed']}/{summary['total_cases']})")
    print(f"Avg score:  {summary['avg_score']:.3f}")
    print()
    print("Per-check pass rates:")
    for check, rate in summary.get("per_check", {}).items():
        print(f"  {check:25s} {rate:.1%}")
    print()
    print("Per-category pass rates:")
    for cat, data in summary.get("per_category", {}).items():
        print(f"  {cat:15s} {data['pass_rate']:.1%} ({data['passed']}/{data['total']})")

    if judge_summary:
        print()
        print("LLM Judge averages:")
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
