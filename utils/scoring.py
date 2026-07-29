"""
Turns a list of LabResult into: a 0-100 health score, per-condition risk
levels, a readable summary, and generic lifestyle recommendations.

# ponytail: health score is a hand-weighted formula (CATEGORY_WEIGHTS),
# not a trained model. Ceiling: weights are a reasonable clinical
# approximation, not validated against outcome data. Upgrade path: once
# there's a labeled dataset (score vs. real outcome), swap this function
# for a fitted regressor -- LabResult -> score is already the exact
# interface a model would need.
"""
from __future__ import annotations

from models.lab_reference import CATEGORY_WEIGHTS, LAB_TESTS, RISK_FACTORS

FLAG_PENALTY = {"normal": 0, "low": 15, "high": 15, "critical": 35}


def health_score(results: list) -> int:
    if not results:
        return 100  # nothing abnormal to report because nothing was found
    by_category: dict[str, list] = {}
    for r in results:
        cat = LAB_TESTS[r.test]["category"]
        by_category.setdefault(cat, []).append(r)

    score = 100.0
    for cat, items in by_category.items():
        weight = CATEGORY_WEIGHTS.get(cat, 0)
        if weight == 0:
            continue
        # average penalty within the category, scaled by that category's weight
        avg_penalty = sum(FLAG_PENALTY[r.flag] for r in items) / len(items)
        score -= avg_penalty * weight
    return max(0, min(100, round(score)))


def assess_risks(results: list) -> list[dict]:
    by_test = {r.test: r for r in results}
    risks = []
    for condition, tests in RISK_FACTORS.items():
        relevant = [by_test[t] for t in tests if t in by_test]
        if not relevant:
            continue
        abnormal = [r for r in relevant if r.flag != "normal"]
        if not abnormal:
            level, confidence = "low", 0.9
        elif any(r.flag == "critical" for r in abnormal):
            level, confidence = "high", 0.75
        else:
            level, confidence = "moderate", 0.6
        risks.append({
            "condition": condition,
            "level": level,
            "confidence": confidence,
            "based_on": [r.label for r in relevant],
        })
    return risks


def generate_summary(results: list, score: int) -> str:
    abnormal = [r for r in results if r.flag != "normal"]
    if not results:
        return ("No lab values could be automatically detected in this report. "
                "Try a clearer scan or check that test names match standard lab wording.")
    if not abnormal:
        return (f"Your report looks mostly normal, with a health score of {score}/100. "
                "All detected values fall within standard reference ranges.")
    parts = []
    for r in abnormal[:4]:
        direction = "elevated" if r.flag in ("high", "critical") else "below the recommended range"
        parts.append(f"{r.label} is {direction} ({r.value} {r.unit})")
    body = "; ".join(parts)
    return (f"Your report has a health score of {score}/100. {body}. "
            "Consider discussing these findings with your healthcare provider.")


def generate_recommendations(results: list) -> list[str]:
    cats_flagged = {LAB_TESTS[r.test]["category"] for r in results if r.flag != "normal"}
    recs = []
    if "diabetes" in cats_flagged:
        recs.append("Reduce refined sugar intake and monitor blood glucose regularly.")
    if "cholesterol" in cats_flagged:
        recs.append("Favor unsaturated fats and increase fiber intake; consider regular cardio exercise.")
    if "blood" in cats_flagged:
        recs.append("Include iron- and B12-rich foods; ask your doctor about a follow-up CBC.")
    if "kidney" in cats_flagged:
        recs.append("Stay well hydrated and moderate sodium/protein intake.")
    if "liver" in cats_flagged:
        recs.append("Limit alcohol intake and follow up with a liver function panel.")
    if "vitamins" in cats_flagged:
        recs.append("Consider sensible sun exposure and a vitamin-rich diet; ask about supplementation.")
    if "thyroid" in cats_flagged:
        recs.append("Follow up with a thyroid panel and discuss symptoms with your doctor.")
    if not recs:
        recs.append("Keep up your current routine, stay hydrated, and maintain regular checkups.")
    recs.append("This tool does not prescribe medication -- always consult a licensed healthcare professional.")
    return recs
