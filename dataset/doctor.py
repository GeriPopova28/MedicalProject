from flask import Blueprint, jsonify, session, send_file, request
import io
from utils.db import get_db
from utils.auth_helpers import is_doctor

# ReportLab библиотеки за генерирането на PDF-а
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Дефиниране на Блупринта
doctor_bp = Blueprint('doctor', __name__)

# =====================================================
# 1. СТАТИСТИКИ И ДАННИ ЗА ПАЦИЕНТИТЕ
# =====================================================
@doctor_bp.route('/doctor/stats-data')
def doctor_stats_data():
    if not is_doctor():
        return jsonify({"error": "Unauthorized"}), 403

    user_id = session.get("user_id")
    if not user_id:
        return jsonify([]), 200 # Винаги връща масив, за да не гърми Frontend-а

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                r.id AS id,
                p.full_name AS patient_name,
                r.prediction,
                r.confidence,
                r.risk_level,
                r.advice,
                r.explanation,
                r.created_at
            FROM analysis_results r
            JOIN patients p ON r.patient_id = p.id
            ORDER BY r.created_at DESC
        """)

        rows = cursor.fetchall()

        result = [{
            "id": r["id"],
            "patient_name": r["patient_name"],
            "prediction": r["prediction"],
            "confidence": float(r["confidence"] or 0),
            "risk_level": r["risk_level"],
            "advice": r["advice"],
            "explanation": r["explanation"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None
        } for r in rows]

        return jsonify(result) # Винаги връща чист JSON масив

    except Exception as e:
        print("Грешка в stats-data:", e)
        return jsonify([])
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn: conn.close()


# =====================================================
# 2. ГЕНЕРИРАНЕ НА МЕДИЦИНСКИ PDF РЕПОРТ
# =====================================================
@doctor_bp.route('/doctor/generate-pdf/<int:analysis_id>')
def generate_medical_pdf(analysis_id):
    if not is_doctor():
        return "Unauthorized", 403

    conn = None
    cursor = None

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT r.*, p.full_name AS patient_name
            FROM analysis_results r
            JOIN patients p ON r.patient_id = p.id
            WHERE r.id = %s
        """, (analysis_id,))

        result = cursor.fetchone()

        if not result:
            return "No record found", 404

        buffer = io.BytesIO()

        # Зареждане на Arial шрифт за поддръжка на Кирилица в Windows
        pdfmetrics.registerFont(
            TTFont('Arial', r'C:\Windows\Fonts\arial.ttf')
        )

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "title",
            parent=styles["Heading1"],
            fontName="Arial",
            fontSize=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1e3a8a"),
            spaceAfter=10
        )

        normal = ParagraphStyle(
            "normal",
            parent=styles["BodyText"],
            fontName="Arial",
            fontSize=10,
            leading=14
        )

        section = ParagraphStyle(
            "section",
            parent=styles["Heading2"],
            fontName="Arial",
            fontSize=12,
            textColor=colors.HexColor("#1e40af"),
            spaceBefore=10,
            spaceAfter=5
        )

        small = ParagraphStyle(
            "small",
            parent=styles["BodyText"],
            fontSize=8,
            textColor=colors.grey
        )

        story = []

        # БОЛНИЧЕН ХЕДЪР
        story.append(Paragraph("UNIVERSITY HOSPITAL MEDICAL CENTER", title_style))
        story.append(Paragraph("Endocrinology Department • AI Clinical Report", normal))
        story.append(Spacer(1, 10))

        # ТАБЛИЦА С ИНФОРМАЦИЯ ЗА ПАЦИЕНТА
        patient_info = [
            ["Patient", result.get('patient_name', '-')],
            ["Report ID", str(result.get('id', '-'))],
            ["Date", str(result.get('created_at', '-'))],
            ["Risk Level", result.get('risk_level', '-')],
        ]

        table = Table(patient_info, colWidths=[140, 330])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Arial"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))

        story.append(table)
        story.append(Spacer(1, 15))

        # РЕЗУЛТАТИ ОТ ДИАГНОСТИКАТА
        story.append(Paragraph("CLINICAL DIAGNOSIS", section))
        story.append(Paragraph(f"AI Prediction: {result.get('prediction', '-')}", normal))
        story.append(Paragraph(f"Confidence Rate: {result.get('confidence', 0)}%", normal))
        story.append(Paragraph(f"Assigned Risk: {result.get('risk_level', '-')}", normal))

        # ПРЕПОРЪКИ
        story.append(Spacer(1, 10))
        story.append(Paragraph("MEDICAL RECOMMENDATION", section))
        story.append(Paragraph(result.get('advice', '-'), normal))

        # ПОДРОБЕН АНАЛИЗ (EXPLANATION)
        story.append(Paragraph("CLINICAL ANALYSIS", section))
        explanation = (result.get('explanation') or "-").replace("\n", "<br/>")
        story.append(Paragraph(explanation, normal))

        # ДЕКЛАРАЦИЯ ЗА ОГРАНИЧАВАНЕ НА ОТГОВОРНОСТТА
        story.append(Spacer(1, 20))
        story.append(Paragraph(
            "Notice: This is an AI-generated medical evaluation report. It is intended solely for supportive decision-making and strict validation by a licensed medical clinician is required.",
            small
        ))

        # ПОДПИСИ
        story.append(Spacer(1, 15))
        signature = Table([
            ["Attending Physician", "MED-AI System"],
            ["Department: Endocrinology", "Version: 1.0.4"],
            ["Signature: __________________", "Status: Verified"],
        ])

        signature.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Arial"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))

        story.append(signature)

        doc.build(story)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"medical_report_{analysis_id}.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print("PDF ERROR:", e)
        return f"Грешка при генериране на PDF: {str(e)}", 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# =====================================================
# 3. ПОТВЪРЖДЕНИЕ / КОРЕКЦИЯ НА ДИАГНОЗАТА ОТ ЛЕКАР
# =====================================================
@doctor_bp.route('/doctor/diagnosis-decision', methods=['POST'])
def diagnosis_decision():
    if not is_doctor():
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    conn = None
    cursor = None

    try:
        data = request.get_json(silent=True) or {}
        analysis_id = data.get("analysis_id")
        decision = data.get("decision") # Напр. 'Approved' или 'Rejected'

        if analysis_id is None or decision is None:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE analysis_results
            SET doctor_decision = %s
            WHERE id = %s
        """, (decision, analysis_id))

        conn.commit()
        return jsonify({"success": True, "message": "Decision saved successfully"})

    except Exception as e:
        if conn: conn.rollback()
        print("ERROR inside diagnosis_decision:", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()