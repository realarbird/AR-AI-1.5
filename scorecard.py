"""
Scorecard & Quality Assurance Module for AR AI 1.5.
Mathematically measures server voice compliance:
- Lowercase %
- Zero comma %
- Zero trailing period %
- Slang & emoji density
- Anti-depression & energetic sentiment score
"""

from typing import List, Dict, Any
import re

SLANG_WORDS = {
    "ngl", "fr", "smp", "ts", "mb", "fym", "tbf", "imo", "cooked", "w", "l",
    "bruh", "bro", "lmao", "lol", "gg", "meta", "bet", "goat", "clutch", "cap", "no cap"
}

EMOJIS = {"💀", "😭", "🔥", "🙏", "👑", "👀", "💯", "🐐"}

DEPRESSED_PATTERNS = [
    r"^\s*yes\s*$",
    r"^\s*no\s*$",
    r"^\s*i guess\s*$",
    r"^\s*idk\s*$",
    r"^\s*whatever\s*$",
    r"^\s*sure\s*$",
    r"^\s*ok\s*$",
    r"^\s*maybe\s*$"
]

def score_response(text: str) -> Dict[str, Any]:
    if not text:
        return {"passed": False, "score": 0.0, "reason": "empty response"}

    is_lower = (text == text.lower())
    no_commas = ("," not in text)
    no_trailing_period = not text.endswith(".")
    no_semicolons = (";" not in text)

    words = text.split()
    word_count = len(words)
    slang_count = sum(1 for w in words if w.strip("!?,.") in SLANG_WORDS)
    emoji_count = sum(1 for ch in text if ch in EMOJIS)

    # Anti-depression check: Ensure response is NOT a flat 1-word reply
    is_depressed = any(re.match(p, text, re.IGNORECASE) for p in DEPRESSED_PATTERNS) or (word_count < 2 and text in ["yes", "no", "ok", "sure", "idk"])
    is_energetic = (word_count >= 3) and not is_depressed

    # Calculate compliance score (0 - 100)
    score = 0
    if is_lower: score += 25
    if no_commas: score += 20
    if no_trailing_period: score += 15
    if no_semicolons: score += 10
    if not is_depressed: score += 20
    if slang_count > 0 or emoji_count > 0 or word_count >= 4: score += 10

    passed = (score >= 80) and not is_depressed

    return {
        "text": text,
        "score": score,
        "passed": passed,
        "is_lowercase": is_lower,
        "no_commas": no_commas,
        "no_trailing_period": no_trailing_period,
        "is_depressed": is_depressed,
        "is_energetic": is_energetic,
        "word_count": word_count,
        "slang_count": slang_count,
        "emoji_count": emoji_count
    }


def evaluate_batch(responses: List[str]) -> Dict[str, Any]:
    scores = [score_response(r) for r in responses]
    total_passed = sum(1 for s in scores if s["passed"])
    avg_score = sum(s["score"] for s in scores) / max(len(scores), 1)
    depressed_count = sum(1 for s in scores if s["is_depressed"])
    lowercase_pct = (sum(1 for s in scores if s["is_lowercase"]) / max(len(scores), 1)) * 100
    zero_comma_pct = (sum(1 for s in scores if s["no_commas"]) / max(len(scores), 1)) * 100

    return {
        "total_evaluated": len(responses),
        "total_passed": total_passed,
        "pass_rate_pct": (total_passed / max(len(scores), 1)) * 100,
        "average_score": avg_score,
        "depressed_count": depressed_count,
        "lowercase_pct": lowercase_pct,
        "zero_comma_pct": zero_comma_pct,
        "details": scores
    }


if __name__ == "__main__":
    sample = [
        "ar bird built me using apple mlx on his mac bro cooked ngl",
        "subtract 5 from both sides 3x = 15 then divide by 3 x = 5",
        "yes",
        "bro types like his keyboard is missing half the keys and the rest are sticky 💀"
    ]
    res = evaluate_batch(sample)
    print(f"Evaluated {res['total_evaluated']} samples. Pass rate: {res['pass_rate_pct']:.1f}%. Avg score: {res['average_score']:.1f}")
    for d in res["details"]:
        status = 'PASS' if d['passed'] else 'FAIL'
        print(f"[{status}] Score: {d['score']} | Depressed: {d['is_depressed']} | '{d['text']}'")
