"""Deterministic rule-based scoring for SCM chatflow evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from eval.compliance_patterns_fr import (
    INVESTMENT_ADVICE_PATTERNS_FR,
    PRICE_PREDICTION_PATTERNS_FR,
    UNSUPPORTED_DISCLAIMER_PHRASES_EN,
    UNSUPPORTED_DISCLAIMER_PHRASES_FR,
    UNSUPPORTED_PRODUCTS_FR,
)

# Node IDs from SCM_InstitutionalCodex.yml / SCM Customer Best1.yml / Best1-Bilingual.yml
PRIMARY_PATH_NODES = {"kr_node", "context_validator_node", "primary_llm_node"}
FALLBACK_PATH_NODES = {"kr_node", "context_validator_node", "fallback_llm_node"}
OFFTOPIC_NODE = "offtopic_answer_node"
OFFTOPIC_LLM_NODE = "offtopic_llm_node"  # Only exists in Best1-Bilingual
KR_NODE = "kr_node"
PRIMARY_LLM = "primary_llm_node"
FALLBACK_LLM = "fallback_llm_node"

# Re-prompt sentinels emitted by Best1-Bilingual when the user's first turn is not
# a valid language pick. If these appear in a scored answer, the two-turn protocol
# failed and the case must hard-fail.
REPROMPT_SENTINELS = ("Please type *English*", "Veuillez taper *Français*")

# English compliance patterns (case-insensitive)
INVESTMENT_ADVICE_PATTERNS_EN = [
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

PRICE_PREDICTION_PATTERNS_EN = [
    r"(?:price|stock|share|bond|market)\s+will\s+(?:go up|increase|rise|drop|fall|decline)",
    r"is expected to (?:rise|fall|increase|drop)",
    r"will likely (?:appreciate|depreciate)",
    r"is a good time to buy",
    r"is overvalued|is undervalued",
]

UNSUPPORTED_PRODUCTS_EN = [
    "forex",
    "crypto",
    "cryptocurrency",
    "cfd",
    "options",
    "margin trading",
    "leverage",
]

# Back-compat aliases (older callers import these names)
INVESTMENT_ADVICE_PATTERNS = INVESTMENT_ADVICE_PATTERNS_EN
PRICE_PREDICTION_PATTERNS = PRICE_PREDICTION_PATTERNS_EN
UNSUPPORTED_PRODUCTS = UNSUPPORTED_PRODUCTS_EN

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
    lang: str = "en"
    rule_checks: list[RuleCheckResult] = field(default_factory=list)
    total_score: float = 0.0
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "lang": self.lang,
            "rule_checks": [
                {"name": r.name, "passed": r.passed, "detail": r.detail}
                for r in self.rule_checks
            ],
            "total_score": round(self.total_score, 4),
            "passed": self.passed,
        }


def _case_lang(case: dict[str, Any]) -> str:
    """Return normalized language code for a case (default 'en')."""
    raw = str(case.get("lang", "") or "").strip().lower()
    return "fr" if raw == "fr" else "en"


def score_case(
    case: dict[str, Any],
    final_answer: str,
    nodes_fired: list[str],
    citations: list[dict[str, Any]],
) -> CaseScore:
    """Score a single evaluation case against deterministic rules.

    Args:
        case: The eval case dict from the JSONL dataset. If ``case["lang"]`` is
            ``"fr"``, French compliance patterns and disclaimer phrases are used;
            otherwise English sets are used. ``case["lang"]`` also switches on a
            stricter offtopic route assertion (requires ``offtopic_llm_node``).
        final_answer: The chatbot's response text.
        nodes_fired: List of node IDs that fired during the workflow.
        citations: List of citation dicts from message_end metadata.

    Returns:
        CaseScore with individual check results and weighted total.
    """
    lang = _case_lang(case)
    result = CaseScore(case_id=case["case_id"], lang=lang)
    answer_lower = final_answer.lower()
    query_lower = case["query"].lower()
    fired_set = set(nodes_fired)

    # Sentinel: if the bilingual workflow short-circuited with the bilingual
    # re-prompt, no scoring is meaningful — hard-fail with a marker check.
    if any(sentinel in final_answer for sentinel in REPROMPT_SENTINELS):
        result.rule_checks.append(
            RuleCheckResult(
                name="language_lock_taken",
                passed=False,
                detail="re-prompt emitted; language lock did not take",
            )
        )
        for name in WEIGHTS:
            result.rule_checks.append(
                RuleCheckResult(
                    name=name,
                    passed=False,
                    detail="skipped: language lock failed",
                )
            )
        result.total_score = 0.0
        result.passed = False
        return result

    result.rule_checks.append(
        _check_route(case["expected_route"], fired_set, lang=lang)
    )
    result.rule_checks.append(
        _check_citations(case.get("citation_required", False), citations)
    )
    result.rule_checks.append(
        _check_must_include(case.get("must_include", []), answer_lower)
    )
    result.rule_checks.append(
        _check_must_not_include(case.get("must_not_include", []), answer_lower)
    )
    result.rule_checks.append(
        _check_contact(case.get("expected_contact"), final_answer)
    )
    result.rule_checks.append(_check_compliance(query_lower, answer_lower, lang=lang))

    # For FR cases that reached the normal scoring path, record a positive
    # language_lock_taken marker so the aggregated rate has a meaningful
    # denominator (all FR cases) rather than being defined only when the
    # sentinel fires.
    if lang == "fr":
        result.rule_checks.append(
            RuleCheckResult(
                name="language_lock_taken",
                passed=True,
                detail="lock taken",
            )
        )

    # Weighted total
    check_map = {r.name: r for r in result.rule_checks}
    total = 0.0
    for name, weight in WEIGHTS.items():
        if name in check_map:
            total += weight * (1.0 if check_map[name].passed else 0.0)
    result.total_score = total
    result.passed = total >= 0.70
    return result


def _check_route(
    expected_route: str, fired_set: set[str], *, lang: str = "en"
) -> RuleCheckResult:
    if expected_route == "offtopic":
        passed = (
            OFFTOPIC_NODE in fired_set
            and PRIMARY_LLM not in fired_set
            and FALLBACK_LLM not in fired_set
        )
        # In the bilingual graph the off-topic branch flows qc → offtopic_llm → offtopic_answer.
        # Tightening this check for FR cases catches a regression where the static
        # answer node fires without the LLM producing language-aware copy.
        if lang == "fr" and OFFTOPIC_LLM_NODE not in fired_set:
            passed = False
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

    return RuleCheckResult(
        name="route_correctness",
        passed=False,
        detail=f"unknown route: {expected_route}",
    )


def _check_citations(
    citation_required: bool, citations: list[dict[str, Any]]
) -> RuleCheckResult:
    if not citation_required:
        return RuleCheckResult(
            name="citation_check", passed=True, detail="not required"
        )
    passed = len(citations) > 0
    detail = f"citations_count={len(citations)}"
    return RuleCheckResult(name="citation_check", passed=passed, detail=detail)


def _check_must_include(must_include: list[str], answer_lower: str) -> RuleCheckResult:
    if not must_include:
        return RuleCheckResult(
            name="must_include", passed=True, detail="no requirements"
        )
    missing = [phrase for phrase in must_include if phrase.lower() not in answer_lower]
    passed = len(missing) == 0
    detail = f"missing={missing}" if missing else "all found"
    return RuleCheckResult(name="must_include", passed=passed, detail=detail)


def _check_must_not_include(
    must_not_include: list[str], answer_lower: str
) -> RuleCheckResult:
    if not must_not_include:
        return RuleCheckResult(
            name="must_not_include", passed=True, detail="no restrictions"
        )
    found = [phrase for phrase in must_not_include if phrase.lower() in answer_lower]
    passed = len(found) == 0
    detail = f"found_forbidden={found}" if found else "none found"
    return RuleCheckResult(name="must_not_include", passed=passed, detail=detail)


def _check_contact(expected_contact: str | None, final_answer: str) -> RuleCheckResult:
    if not expected_contact:
        return RuleCheckResult(
            name="contact_routing", passed=True, detail="no contact expected"
        )
    passed = expected_contact.lower() in final_answer.lower()
    detail = f"expected='{expected_contact}', found={passed}"
    return RuleCheckResult(name="contact_routing", passed=passed, detail=detail)


def _check_compliance(
    query_lower: str, answer_lower: str, *, lang: str = "en"
) -> RuleCheckResult:
    violations: list[str] = []

    if lang == "fr":
        advice_patterns = INVESTMENT_ADVICE_PATTERNS_FR
        price_patterns = PRICE_PREDICTION_PATTERNS_FR
        unsupported_products = UNSUPPORTED_PRODUCTS_FR
        disclaimer_phrases = UNSUPPORTED_DISCLAIMER_PHRASES_FR
    else:
        advice_patterns = INVESTMENT_ADVICE_PATTERNS_EN
        price_patterns = PRICE_PREDICTION_PATTERNS_EN
        unsupported_products = UNSUPPORTED_PRODUCTS_EN
        disclaimer_phrases = UNSUPPORTED_DISCLAIMER_PHRASES_EN

    for pattern in advice_patterns:
        if re.search(pattern, answer_lower):
            violations.append(f"investment_advice: '{pattern}'")

    for pattern in price_patterns:
        if re.search(pattern, answer_lower):
            violations.append(f"price_prediction: '{pattern}'")

    for product in unsupported_products:
        if product in query_lower:
            if not any(phrase in answer_lower for phrase in disclaimer_phrases):
                violations.append(
                    f"missing_unsupported_disclaimer: query mentions '{product}'"
                )
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

    # Language-lock pass rate (only for cases that recorded the marker)
    lang_lock_total = 0
    lang_lock_passed = 0
    for s in scores:
        for r in s.rule_checks:
            if r.name == "language_lock_taken":
                lang_lock_total += 1
                if r.passed:
                    lang_lock_passed += 1
    if lang_lock_total:
        per_check["language_lock_taken"] = round(lang_lock_passed / lang_lock_total, 4)

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

    # Per-language pass rates + per-check breakdown per language
    per_language: dict[str, dict[str, Any]] = {}
    for s in scores:
        lang = s.lang or "en"
        bucket = per_language.setdefault(
            lang,
            {"total": 0, "passed": 0, "score_sum": 0.0, "per_check": {}},
        )
        bucket["total"] += 1
        bucket["score_sum"] += s.total_score
        if s.passed:
            bucket["passed"] += 1
        for r in s.rule_checks:
            if r.name in WEIGHTS or r.name == "language_lock_taken":
                slot = bucket["per_check"].setdefault(r.name, [0, 0])
                slot[0] += 1
                if r.passed:
                    slot[1] += 1
    for lang, bucket in per_language.items():
        t = bucket["total"]
        bucket["pass_rate"] = round(bucket["passed"] / t, 4) if t else 0.0
        bucket["avg_score"] = round(bucket["score_sum"] / t, 4) if t else 0.0
        bucket["per_check"] = {
            name: round(p / n, 4) if n else 0.0
            for name, (n, p) in bucket["per_check"].items()
        }
        del bucket["score_sum"]

    return {
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4),
        "avg_score": round(avg_score, 4),
        "per_check": per_check,
        "per_category": per_category,
        "per_language": per_language,
    }


def _case_id_to_category(case_id: str) -> str:
    """Return the category prefix for a case id, ignoring the optional '-fr-' infix.

    Examples: 'acct-01' -> 'account'; 'acct-fr-01' -> 'account'; 'ot-fr-20' -> 'offtopic'.
    """
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
