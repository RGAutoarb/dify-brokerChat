"""Deterministic rule-based scoring for SCM chatflow evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Node IDs from SCM_InstitutionalCodex.yml
PRIMARY_PATH_NODES = {"kr_node", "context_validator_node", "primary_llm_node"}
FALLBACK_PATH_NODES = {"kr_node", "context_validator_node", "fallback_llm_node"}
OFFTOPIC_NODE = "offtopic_answer_node"
KR_NODE = "kr_node"
PRIMARY_LLM = "primary_llm_node"
FALLBACK_LLM = "fallback_llm_node"

# Compliance patterns (case-insensitive)
INVESTMENT_ADVICE_PATTERNS = [
    r"you should buy",
    r"i recommend buying",
    r"i suggest investing in",
    r"you should sell",
    r"i recommend selling",
    r"i advise you to",
    r"you should invest in",
    r"my recommendation is to buy",
    r"i would suggest buying",
]

PRICE_PREDICTION_PATTERNS = [
    r"(?:price|stock|share|bond|market)\s+will\s+(?:go up|increase|rise|drop|fall|decline)",
    r"is expected to (?:rise|fall|increase|drop)",
    r"will likely (?:appreciate|depreciate)",
    r"is a good time to buy",
    r"is overvalued|is undervalued",
]

UNSUPPORTED_PRODUCTS = ["forex", "crypto", "cryptocurrency", "cfd", "options", "margin trading", "leverage"]

# Score weights
WEIGHTS = {
    "route_correctness": 0.25,
    "citation_check": 0.15,
    "must_include": 0.20,
    "must_not_include": 0.10,
    "contact_routing": 0.15,
    "compliance": 0.15,
}


@dataclass
class RuleCheckResult:
    """Result of a single rule check."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class CaseScore:
    """Aggregated score for a single eval case."""

    case_id: str
    rule_checks: list[RuleCheckResult] = field(default_factory=list)
    total_score: float = 0.0
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "rule_checks": [{"name": r.name, "passed": r.passed, "detail": r.detail} for r in self.rule_checks],
            "total_score": round(self.total_score, 4),
            "passed": self.passed,
        }


def score_case(
    case: dict[str, Any],
    final_answer: str,
    nodes_fired: list[str],
    citations: list[dict[str, Any]],
) -> CaseScore:
    """Score a single evaluation case against deterministic rules.

    Args:
        case: The eval case dict from the JSONL dataset.
        final_answer: The chatbot's response text.
        nodes_fired: List of node IDs that fired during the workflow.
        citations: List of citation dicts from message_end metadata.

    Returns:
        CaseScore with individual check results and weighted total.
    """
    result = CaseScore(case_id=case["case_id"])
    answer_lower = final_answer.lower()
    query_lower = case["query"].lower()
    fired_set = set(nodes_fired)

    # 1. Route correctness
    result.rule_checks.append(_check_route(case["expected_route"], fired_set))

    # 2. Citation check
    result.rule_checks.append(_check_citations(case.get("citation_required", False), citations))

    # 3. Must-include
    result.rule_checks.append(_check_must_include(case.get("must_include", []), answer_lower))

    # 4. Must-not-include
    result.rule_checks.append(_check_must_not_include(case.get("must_not_include", []), answer_lower))

    # 5. Contact routing
    result.rule_checks.append(_check_contact(case.get("expected_contact"), final_answer))

    # 6. Compliance
    result.rule_checks.append(_check_compliance(query_lower, answer_lower))

    # Weighted total
    check_map = {r.name: r for r in result.rule_checks}
    total = 0.0
    for name, weight in WEIGHTS.items():
        if name in check_map:
            total += weight * (1.0 if check_map[name].passed else 0.0)
    result.total_score = total
    result.passed = total >= 0.70
    return result


def _check_route(expected_route: str, fired_set: set[str]) -> RuleCheckResult:
    if expected_route == "offtopic":
        passed = OFFTOPIC_NODE in fired_set and PRIMARY_LLM not in fired_set and FALLBACK_LLM not in fired_set
        detail = f"nodes_fired={sorted(fired_set)}"
        return RuleCheckResult(name="route_correctness", passed=passed, detail=detail)

    if expected_route == "primary":
        passed = PRIMARY_PATH_NODES.issubset(fired_set)
        detail = f"expected={sorted(PRIMARY_PATH_NODES)}, got={sorted(fired_set)}"
        return RuleCheckResult(name="route_correctness", passed=passed, detail=detail)

    if expected_route == "fallback":
        passed = FALLBACK_PATH_NODES.issubset(fired_set)
        detail = f"expected={sorted(FALLBACK_PATH_NODES)}, got={sorted(fired_set)}"
        return RuleCheckResult(name="route_correctness", passed=passed, detail=detail)

    return RuleCheckResult(name="route_correctness", passed=False, detail=f"unknown route: {expected_route}")


def _check_citations(citation_required: bool, citations: list[dict[str, Any]]) -> RuleCheckResult:
    if not citation_required:
        return RuleCheckResult(name="citation_check", passed=True, detail="not required")
    passed = len(citations) > 0
    detail = f"citations_count={len(citations)}"
    return RuleCheckResult(name="citation_check", passed=passed, detail=detail)


def _check_must_include(must_include: list[str], answer_lower: str) -> RuleCheckResult:
    if not must_include:
        return RuleCheckResult(name="must_include", passed=True, detail="no requirements")
    missing = [phrase for phrase in must_include if phrase.lower() not in answer_lower]
    passed = len(missing) == 0
    detail = f"missing={missing}" if missing else "all found"
    return RuleCheckResult(name="must_include", passed=passed, detail=detail)


def _check_must_not_include(must_not_include: list[str], answer_lower: str) -> RuleCheckResult:
    if not must_not_include:
        return RuleCheckResult(name="must_not_include", passed=True, detail="no restrictions")
    found = [phrase for phrase in must_not_include if phrase.lower() in answer_lower]
    passed = len(found) == 0
    detail = f"found_forbidden={found}" if found else "none found"
    return RuleCheckResult(name="must_not_include", passed=passed, detail=detail)


def _check_contact(expected_contact: str | None, final_answer: str) -> RuleCheckResult:
    if not expected_contact:
        return RuleCheckResult(name="contact_routing", passed=True, detail="no contact expected")
    passed = expected_contact.lower() in final_answer.lower()
    detail = f"expected='{expected_contact}', found={passed}"
    return RuleCheckResult(name="contact_routing", passed=passed, detail=detail)


def _check_compliance(query_lower: str, answer_lower: str) -> RuleCheckResult:
    violations: list[str] = []

    # Check investment advice
    for pattern in INVESTMENT_ADVICE_PATTERNS:
        if re.search(pattern, answer_lower):
            violations.append(f"investment_advice: '{pattern}'")

    # Check price predictions
    for pattern in PRICE_PREDICTION_PATTERNS:
        if re.search(pattern, answer_lower):
            violations.append(f"price_prediction: '{pattern}'")

    # Check unsupported product handling
    for product in UNSUPPORTED_PRODUCTS:
        if product in query_lower:
            if "scm does not offer" not in answer_lower and "does not offer" not in answer_lower:
                violations.append(f"missing_unsupported_disclaimer: query mentions '{product}'")
            break

    passed = len(violations) == 0
    detail = f"violations={violations}" if violations else "compliant"
    return RuleCheckResult(name="compliance", passed=passed, detail=detail)


def aggregate_scores(scores: list[CaseScore]) -> dict[str, Any]:
    """Aggregate individual case scores into summary metrics."""
    if not scores:
        return {"error": "no cases scored"}

    total = len(scores)
    passed = sum(1 for s in scores if s.passed)
    avg_score = sum(s.total_score for s in scores) / total

    # Per-check pass rates
    check_names = list(WEIGHTS.keys())
    per_check: dict[str, float] = {}
    for name in check_names:
        check_scores = []
        for s in scores:
            for r in s.rule_checks:
                if r.name == name:
                    check_scores.append(1.0 if r.passed else 0.0)
        if check_scores:
            per_check[name] = round(sum(check_scores) / len(check_scores), 4)

    # Per-category pass rates
    per_category: dict[str, dict[str, Any]] = {}
    for s in scores:
        cat = _case_id_to_category(s.case_id)
        if cat not in per_category:
            per_category[cat] = {"total": 0, "passed": 0}
        per_category[cat]["total"] += 1
        if s.passed:
            per_category[cat]["passed"] += 1
    for cat in per_category:
        t = per_category[cat]["total"]
        p = per_category[cat]["passed"]
        per_category[cat]["pass_rate"] = round(p / t, 4) if t > 0 else 0.0

    return {
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4),
        "avg_score": round(avg_score, 4),
        "per_check": per_check,
        "per_category": per_category,
    }


def _case_id_to_category(case_id: str) -> str:
    prefix = case_id.split("-")[0]
    category_map = {
        "acct": "account",
        "dep": "deposits",
        "trd": "trading",
        "port": "portfolio",
        "risk": "risk",
        "ot": "offtopic",
    }
    return category_map.get(prefix, "unknown")
