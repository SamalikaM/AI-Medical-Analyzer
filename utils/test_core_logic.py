"""
Runnable self-check for extraction.py + scoring.py.
Usage: python utils/test_core_logic.py   (run from project root)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.extraction import extract_all, looks_like_medical_report
from utils.scoring import health_score, assess_risks, generate_summary, generate_recommendations

SAMPLE_REPORT = """
Patient Name: John Doe
Age: 45
Gender: Male
Doctor: Dr. Sarah Khan
Hospital: City General Hospital
Report Date: 01/15/2026

Test Name          Value   Unit    Reference Range
Hemoglobin          10.2    g/dL    12.0-16.5
WBC                 7.5     thousand/uL  4.0-11.0
Glucose Fasting     145     mg/dL   70-100
Cholesterol Total   240     mg/dL   0-200
Vitamin D           18      ng/mL   30-100
Creatinine          1.0     mg/dL   0.6-1.3
"""

def main():
    result = extract_all(SAMPLE_REPORT)

    assert result.patient_info.get("name") == "John Doe", result.patient_info
    assert result.patient_info.get("age") == "45", result.patient_info
    assert result.patient_info.get("gender", "").lower() == "male"

    by_test = {r.test: r for r in result.lab_results}
    assert "hemoglobin" in by_test and by_test["hemoglobin"].flag == "low"
    assert by_test["glucose"].flag == "high"
    assert by_test["cholesterol"].flag == "high"
    assert by_test["vitamin_d"].flag == "low"
    assert by_test["creatinine"].flag == "normal"
    assert len(result.lab_results) == 6, f"expected 6 values, got {len(result.lab_results)}"

    score = health_score(result.lab_results)
    assert 0 <= score <= 100
    assert score < 100, "abnormal values present, score should be penalized"

    risks = assess_risks(result.lab_results)
    risk_names = {r["condition"] for r in risks}
    assert "Diabetes" in risk_names
    assert "Anemia" in risk_names

    summary = generate_summary(result.lab_results, score)
    assert "health score" in summary.lower()

    recs = generate_recommendations(result.lab_results)
    assert any("medication" in r.lower() for r in recs)

    # edge case: empty text should not crash, should return no results
    empty = extract_all("")
    assert empty.lab_results == []
    assert health_score(empty.lab_results) == 100

    # invalid-document gate: a real report passes, unrelated text fails
    assert looks_like_medical_report(result, SAMPLE_REPORT) is True
    junk_text = "Thanks for shopping at SuperMart! Total: $42.19. Visa ending 1234."
    junk_result = extract_all(junk_text)
    assert looks_like_medical_report(junk_result, junk_text) is False

    print(f"All checks passed. Sample health score: {score}/100")
    print(f"Detected {len(result.lab_results)} lab values, {len(risks)} risk factors flagged.")

if __name__ == "__main__":
    main()
