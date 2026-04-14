"""Optional LLM-as-judge via OpenRouter for semantic evaluation scoring."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-5-mini"

RUBRIC_PROMPT = """\
You are an evaluation judge for a customer support chatbot for Sahel Capital Markets (SCM), \
a West African brokerage offering equities and bonds.

Score the chatbot's answer on four dimensions (0.0 to 1.0 each):

1. **correctness**: Does the answer accurately reflect the reference answer and facts? \
   1.0 = fully correct, 0.0 = completely wrong or fabricated.
2. **groundedness**: Is the answer grounded in the provided citations/context, or does it \
   hallucinate facts not present? 1.0 = fully grounded, 0.0 = entirely hallucinated.
3. **completeness**: Does the answer address all parts of the user's question? \
   1.0 = fully complete, 0.0 = misses the question entirely.
4. **tone**: Is the answer professional, concise, and appropriate for customer support? \
   1.0 = excellent tone, 0.0 = rude, verbose, or unprofessional.

Respond ONLY with valid JSON in this exact format:
{
  "correctness": <float 0-1>,
  "groundedness": <float 0-1>,
  "completeness": <float 0-1>,
  "tone": <float 0-1>,
  "explanation": "<one sentence summary>"
}
"""


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
        api_key: OpenRouter API key. Falls back to OPENROUTER_API_KEY env var.
        model: OpenRouter model identifier.
        timeout: Request timeout in seconds.

    Returns:
        JudgeScores with 0-1 scores per dimension, or error if judge call fails.
    """
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return JudgeScores(error="No OPENROUTER_API_KEY set")

    citations_text = "\n".join(
        c.get("content", c.get("segment_content", str(c)))[:300] for c in citations[:5]
    ) if citations else "(no citations returned)"

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
            {"role": "system", "content": RUBRIC_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0,
        "max_tokens": 300,
    }

    try:
        resp = httpx.post(OPENROUTER_URL, headers=headers, json=payload, timeout=timeout)
        if resp.status_code != 200:
            return JudgeScores(error=f"HTTP {resp.status_code}: {resp.text[:300]}")

        content = resp.json()["choices"][0]["message"]["content"].strip()
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
        return {"correctness": None, "groundedness": None, "completeness": None, "tone": None, "judged_count": 0}

    dims = ["correctness", "groundedness", "completeness", "tone"]
    result: dict[str, float | None] = {}
    for dim in dims:
        vals = [getattr(s, dim) for s in valid if getattr(s, dim) is not None]
        result[dim] = round(sum(vals) / len(vals), 4) if vals else None
    result["judged_count"] = len(valid)
    result["judge_errors"] = len(scores) - len(valid)
    return result
