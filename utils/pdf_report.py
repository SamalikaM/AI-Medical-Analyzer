"""Builds the downloadable PDF summary of a single analyzed report."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

FLAG_COLOR = {
    "normal": colors.HexColor("#2e7d32"),
    "low": colors.HexColor("#f9a825"),
    "high": colors.HexColor("#ef6c00"),
    "critical": colors.HexColor("#c62828"),
}


def build_pdf_report(output_path, patient_info, lab_results, score, risks, summary, recommendations):
    doc = SimpleDocTemplate(output_path, pagesize=letter, title="Health Report")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleBlue", parent=styles["Title"], textColor=colors.HexColor("#1565c0"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=colors.HexColor("#1565c0"))

    elements = [
        Paragraph("Health Insights Report", title_style),
        Spacer(1, 10),
    ]

    if patient_info:
        rows = [[k.replace("_", " ").title(), v] for k, v in patient_info.items()]
        pt = Table(rows, colWidths=[150, 300])
        pt.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements += [Paragraph("Patient Information", h2), pt, Spacer(1, 14)]

    elements += [Paragraph(f"Health Score: {score}/100", h2), Spacer(1, 8)]

    if lab_results:
        data = [["Test", "Value", "Unit", "Normal Range", "Status"]]
        for r in lab_results:
            data.append([r["label"], str(r["value"]), r["unit"],
                         f"{r['low']}-{r['high']}", r["flag"].title()])
        table = Table(data, colWidths=[110, 60, 70, 100, 80])
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f8fc")]),
        ]
        for i, r in enumerate(lab_results, start=1):
            style_cmds.append(("TEXTCOLOR", (4, i), (4, i), FLAG_COLOR.get(r["flag"], colors.black)))
        table.setStyle(TableStyle(style_cmds))
        elements += [Paragraph("Laboratory Values", h2), table, Spacer(1, 14)]

    if risks:
        data = [["Condition", "Risk Level", "Confidence"]]
        for r in risks:
            data.append([r["condition"], r["level"].title(), f"{int(r['confidence']*100)}%"])
        rt = Table(data, colWidths=[180, 100, 100])
        rt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements += [Paragraph("Educational Risk Assessment", h2), rt, Spacer(1, 14)]

    elements += [Paragraph("AI Summary", h2), Paragraph(summary, styles["BodyText"]), Spacer(1, 12)]

    if recommendations:
        rec_html = "<br/>".join(f"&#8226; {r}" for r in recommendations)
        elements += [Paragraph("Recommendations", h2), Paragraph(rec_html, styles["BodyText"]), Spacer(1, 12)]

    disclaimer = ParagraphStyle("Disclaimer", parent=styles["BodyText"], textColor=colors.grey, fontSize=8)
    elements.append(Paragraph(
        "Disclaimer: This report is generated for educational purposes only and is NOT a medical "
        "diagnosis. Always consult a licensed healthcare professional regarding any medical concerns.",
        disclaimer,
    ))

    doc.build(elements)
    return output_path
