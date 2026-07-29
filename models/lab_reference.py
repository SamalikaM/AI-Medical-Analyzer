"""
Reference ranges + regex aliases for every lab test we know how to read.
To add a new test: add ONE entry here. Nothing else needs to change
(extraction, flagging, scoring, and the dashboard all read from this table).

low/high define the "normal" band. critical_low/critical_high are optional;
if a value falls outside them the flag becomes "critical" instead of just
"low"/"high". category feeds the health-score weighting in scoring.py.
"""

LAB_TESTS = {
    "hemoglobin": {
        "aliases": [r"h(?:a)?emoglobin", r"\bHb\b"],
        "unit": "g/dL", "low": 12.0, "high": 16.5,
        "critical_low": 7.0, "critical_high": 20.0, "category": "blood",
    },
    "rbc": {
        "aliases": [r"\bRBC\b", r"red\s+blood\s+cell\s*count"],
        "unit": "million/uL", "low": 4.2, "high": 5.9, "category": "blood",
    },
    "wbc": {
        "aliases": [r"\bWBC\b", r"white\s+blood\s+cell\s*count"],
        "unit": "thousand/uL", "low": 4.0, "high": 11.0,
        "critical_low": 2.0, "critical_high": 20.0, "category": "blood",
    },
    "platelets": {
        "aliases": [r"platelets?", r"\bPLT\b"],
        "unit": "thousand/uL", "low": 150, "high": 450,
        "critical_low": 50, "critical_high": 1000, "category": "blood",
    },
    "glucose": {
        "aliases": [r"glucose(?:\s*\(?fasting\)?)?", r"\bFBS\b"],
        "unit": "mg/dL", "low": 70, "high": 100,
        "critical_low": 40, "critical_high": 300, "category": "diabetes",
    },
    "hba1c": {
        "aliases": [r"HbA1c", r"glycated\s+h(?:a)?emoglobin"],
        "unit": "%", "low": 4.0, "high": 5.6,
        "critical_high": 10.0, "category": "diabetes",
    },
    "cholesterol": {
        "aliases": [r"(?:total\s+)?cholesterol"],
        "unit": "mg/dL", "low": 0, "high": 200,
        "critical_high": 300, "category": "cholesterol",
    },
    "hdl": {
        "aliases": [r"\bHDL\b(?:\s+cholesterol)?"],
        "unit": "mg/dL", "low": 40, "high": 90, "category": "cholesterol",
    },
    "ldl": {
        "aliases": [r"\bLDL\b(?:\s+cholesterol)?"],
        "unit": "mg/dL", "low": 0, "high": 130,
        "critical_high": 190, "category": "cholesterol",
    },
    "triglycerides": {
        "aliases": [r"triglycerides?"],
        "unit": "mg/dL", "low": 0, "high": 150,
        "critical_high": 500, "category": "cholesterol",
    },
    "creatinine": {
        "aliases": [r"creatinine"],
        "unit": "mg/dL", "low": 0.6, "high": 1.3,
        "critical_high": 3.0, "category": "kidney",
    },
    "urea": {
        "aliases": [r"urea", r"blood\s+urea(?:\s+nitrogen)?", r"\bBUN\b"],
        "unit": "mg/dL", "low": 7, "high": 20,
        "critical_high": 100, "category": "kidney",
    },
    "bilirubin": {
        "aliases": [r"bilirubin(?:\s*\(?total\)?)?"],
        "unit": "mg/dL", "low": 0.1, "high": 1.2,
        "critical_high": 5.0, "category": "liver",
    },
    "alt": {
        "aliases": [r"\bALT\b", r"SGPT"],
        "unit": "U/L", "low": 7, "high": 56,
        "critical_high": 200, "category": "liver",
    },
    "ast": {
        "aliases": [r"\bAST\b", r"SGOT"],
        "unit": "U/L", "low": 10, "high": 40,
        "critical_high": 200, "category": "liver",
    },
    "vitamin_d": {
        "aliases": [r"vitamin\s*D(?:3)?"],
        "unit": "ng/mL", "low": 30, "high": 100,
        "critical_low": 10, "category": "vitamins",
    },
    "vitamin_b12": {
        "aliases": [r"vitamin\s*B\s*-?12", r"\bB12\b"],
        "unit": "pg/mL", "low": 200, "high": 900,
        "critical_low": 100, "category": "vitamins",
    },
    "tsh": {
        "aliases": [r"\bTSH\b", r"thyroid\s+stimulating\s+hormone"],
        "unit": "uIU/mL", "low": 0.4, "high": 4.0,
        "critical_low": 0.1, "critical_high": 10.0, "category": "thyroid",
    },
    "calcium": {
        "aliases": [r"calcium"],
        "unit": "mg/dL", "low": 8.5, "high": 10.5, "category": "electrolytes",
    },
    "potassium": {
        "aliases": [r"potassium"],
        "unit": "mEq/L", "low": 3.5, "high": 5.1,
        "critical_low": 2.5, "critical_high": 6.5, "category": "electrolytes",
    },
    "sodium": {
        "aliases": [r"sodium"],
        "unit": "mEq/L", "low": 135, "high": 145,
        "critical_low": 120, "critical_high": 160, "category": "electrolytes",
    },
    "urine_protein": {
        "aliases": [r"urine\s+protein"],
        "unit": "mg/dL", "low": 0, "high": 20, "category": "kidney",
    },
    "bmi": {
        "aliases": [r"\bBMI\b", r"body\s+mass\s+index"],
        "unit": "kg/m2", "low": 18.5, "high": 24.9,
        "critical_high": 40, "category": "vitals",
    },
}

# Category -> how much it weighs in the 0-100 health score. Must sum to 1.0.
CATEGORY_WEIGHTS = {
    "blood": 0.20, "kidney": 0.15, "liver": 0.15, "cholesterol": 0.15,
    "diabetes": 0.15, "vitamins": 0.10, "electrolytes": 0.05,
    "thyroid": 0.05, "vitals": 0.0,  # BMI shown but not scored (needs height/weight context)
}

# risk name -> lab categories that feed it (used for the educational risk panel)
RISK_FACTORS = {
    "Anemia": ["hemoglobin", "rbc"],
    "Diabetes": ["glucose", "hba1c"],
    "Heart disease": ["cholesterol", "hdl", "ldl", "triglycerides"],
    "Kidney disease": ["creatinine", "urea", "urine_protein"],
    "Liver issues": ["bilirubin", "alt", "ast"],
    "Vitamin deficiency": ["vitamin_d", "vitamin_b12"],
    "Thyroid disorder": ["tsh"],
    "Hypertension": ["sodium", "potassium"],
}
