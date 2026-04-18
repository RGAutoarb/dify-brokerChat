"""Optional LLM-as-judge via OpenRouter for semantic evaluation scoring."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-5-mini"

RUBRIC_PROMPT_TEMPLATE = """\
You are an evaluation judge for a customer support chatbot for Sahel Capital Markets (SCM), \
a West African brokerage offering equities and bonds.

The case being scored is in language: {lang_name} ({lang_code}).{lang_directive}

Score the chatbot's answer on four dimensions (0.0 to 1.0 each):

1. **correctness**: Does the answer accurately reflect the reference answer and facts? \
   1.0 = fully correct, 0.0 = completely wrong or fabricated. An over-general claim that \
   is wrong for a subset of cases is an inaccuracy (e.g., saying "all equity trades settle \
   T+3" when the reference distinguishes GSE/BRVM T+3 from NSE T+2).
2. **groundedness**: Is the answer grounded in the provided citations/context, or does it \
   hallucinate facts not present? 1.0 = fully grounded, 0.0 = entirely hallucinated.
3. **completeness**: Does the answer include the important facts and distinctions present \
   in the REFERENCE ANSWER? An answer that addresses the literal user question but omits \
   disambiguating context from the reference is NOT complete. Specifically: if the reference \
   contrasts multiple cases (e.g., "GSE/BRVM T+3, NSE T+2"; "Commission 1.5% with min GHS 5"; \
   "Free for mobile money, $15 for international wire"), an answer that covers only one side \
   of the contrast should score at most 0.6. 1.0 = all reference facts preserved, \
   0.0 = misses the question entirely.
4. **tone**: Is the answer professional, concise, and appropriate for customer support? \
   1.0 = excellent tone, 0.0 = rude, verbose, or unprofessional. For French cases, \
   evaluate tone in terms of natural, polite French customer-service register — do not \
   penalise a well-formed French response for being non-English. Penalize heavily (drop to \
   0.5 or below): internal reasoning or chain-of-thought tags leaking into the answer \
   (e.g., <think>, <reasoning>, "**Finalizing...**" meta-commentary), and language-mismatch \
   content (English fragments in a French answer, or French fragments in an English answer).

Respond ONLY with valid JSON in this exact format:
{{
  "correctness": <float 0-1>,
  "groundedness": <float 0-1>,
  "completeness": <float 0-1>,
  "tone": <float 0-1>,
  "explanation": "<one sentence summary in {lang_name}>"
}}
"""

# Back-compat: existing callers that import RUBRIC_PROMPT get the English-default rendering.
RUBRIC_PROMPT = RUBRIC_PROMPT_TEMPLATE.format(
    lang_name="English",
    lang_code="en",
    lang_directive="",
)


def _rubric_prompt_for(lang: str) -> str:
    lang = (lang or "en").lower()
    if lang == "fr":
        return RUBRIC_PROMPT_TEMPLATE.format(
            lang_name="French",
            lang_code="fr",
            lang_directive=(
                " The user query, reference answer, and chatbot answer are all in French; "
                "evaluate the French answer on its own merits and expect the explanation "
                "field to be written in French."
            ),
        )
    return RUBRIC_PROMPT


@dataclass
class JudgeScores:
    correctness: float | None = None
    groundedness: float | None = None
    completeness: float | None = None
    tone: float | None = None
    explanation: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "correctness": self.correctness,
            "groundedness": self.groundedness,
            "completeness": self.completeness,
            "tone": self.tone,
            "explanation": self.explanation,
            "error": self.error,
        }


def judge_case(
    query: str,
    answer: str,
    reference_answer: str,
    citations: list[dict[str, Any]],
    *,
    lang: str = "en",
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    timeout: float = 30.0,
) -> JudgeScores:
    """Score a single case using an LLM judge via OpenRouter.

    Args:
        query: The user's original question.
        answer: The chatbot's response.
        reference_answer: The expected/ideal answer from the dataset.
        citations: List of citation dicts returned by the chatbot.
        lang: Case language (``"en"`` or ``"fr"``). Selects the rubric rendering so the
            judge expects and emits French for French cases.
        api_key: OpenRouter API key. Falls back to OPENROUTER_API_KEY env var.
        model: OpenRouter model identifier.
        timeout: Request timeout in seconds.

    Returns:
        JudgeScores with 0-1 scores per dimension, or error if judge call fails.
    """
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return JudgeScores(error="No OPENROUTER_API_KEY set")

    citations_text = (
        "\n".join(
            c.get("content", c.get("segment_content", str(c)))[:300]
            for c in citations[:5]
        )
        if citations
        else "(no citations returned)"
    )

    user_message = (
        f"USER QUERY:\n{query}\n\n"
        f"CHATBOT ANSWER:\n{answer}\n\n"
        f"REFERENCE ANSWER:\n{reference_answer}\n\n"
        f"CITATIONS RETRIEVED:\n{citations_text}"
    )

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _rubric_prompt_for(lang)},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0,
        # Reasoning models (gpt-5-mini, o-series) count reasoning tokens inside
        # max_tokens. A tight cap starves the JSON output and returns content=null.
        "max_tokens": 1200,
    }

    try:
        resp = httpx.post(
            OPENROUTER_URL, headers=headers, json=payload, timeout=timeout
        )
        if resp.status_code != 200:
            return JudgeScores(error=f"HTTP {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        choices = body.get("choices") or []
        if not choices:
            return JudgeScores(error=f"No choices in judge response: {str(body)[:300]}")
        choice = choices[0]
        finish_reason = choice.get("finish_reason")
        message = choice.get("message") or {}
        raw_content = message.get("content")
        if raw_content is None:
            return JudgeScores(
                error=(
                    f"Empty judge content (finish_reason={finish_reason}, "
                    f"message_keys={sorted(message.keys())})"
                )
            )
        content = raw_content.strip()
        # Extract JSON from response (handle markdown code blocks)
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content)

        return JudgeScores(
            correctness=_clamp(parsed.get("correctness")),
            groundedness=_clamp(parsed.get("groundedness")),
            completeness=_clamp(parsed.get("completeness")),
            tone=_clamp(parsed.get("tone")),
            explanation=parsed.get("explanation", ""),
        )
    except json.JSONDecodeError as exc:
        return JudgeScores(error=f"Failed to parse judge response: {exc}")
    except httpx.TimeoutException:
        return JudgeScores(error=f"Judge timeout after {timeout}s")
    except Exception as exc:
        return JudgeScores(error=f"Judge error: {exc}")


def _clamp(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return max(0.0, min(1.0, float(val)))
    except (TypeError, ValueError):
        return None


def aggregate_judge_scores(scores: list[JudgeScores]) -> dict[str, float | None]:
    """Average judge scores across cases, ignoring errors."""
    valid = [s for s in scores if s.error is None]
    if not valid:
        return {
            "correctness": None,
            "groundedness": None,
            "completeness": None,
            "tone": None,
            "judged_count": 0,
        }

    dims = ["correctness", "groundedness", "completeness", "tone"]
    result: dict[str, float | None] = {}
    for dim in dims:
        vals = [getattr(s, dim) for s in valid if getattr(s, dim) is not None]
        result[dim] = round(sum(vals) / len(vals), 4) if vals else None
    result["judged_count"] = len(valid)
    result["judge_errors"] = len(scores) - len(valid)
    return result
