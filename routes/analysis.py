from flask import Blueprint, request, jsonify
import random
from utils.auth_helpers import is_logged_in
from utils.helpers import safe_float, clamp

analysis_bp = Blueprint('analysis', __name__)

# Памет за куиза (ако се вика вътре в анализа)
used_questions = set()
quiz_bank = [
    {"question": "Пример 1?", "options": ["А", "Б", "В"], "correct": "А"},
    {"question": "Пример 2?", "options": ["Х", "Y", "Z"], "correct": "Х"}
]

@analysis_bp.route("/run-analysis", methods=["POST"])
def run_analysis():
    try:
        if not is_logged_in():
            return jsonify({"error": "Unauthorized"}), 401

        file = request.files.get("file")
        complain = (request.form.get("complain") or "").lower()
        tsh = safe_float(request.form.get("tsh"))
        ft4 = safe_float(request.form.get("ft4"))
        mat = safe_float(request.form.get("mat"))
        tat = safe_float(request.form.get("tat"))

        lab_score = 0.0
        if tsh is not None:
            if tsh > 4.5: lab_score += 0.4
            elif tsh < 0.4: lab_score += 0.35
            else: lab_score += 0.1

        if ft4 is not None:
            if ft4 < 10 or ft4 > 22: lab_score += 0.35
            else: lab_score += 0.1

        if mat is not None and mat > 34: lab_score += 0.2
        if tat is not None and tat > 115: lab_score += 0.2

        lab_score = clamp(lab_score, 0, 1)

        symptoms_map = {
            "fatigue": 0.15, "tired": 0.15, "weight": 0.18, "hair": 0.12,
            "palpitation": 0.2, "anxiety": 0.18, "cold": 0.12, "heat": 0.12
        }
        symptom_score = sum(v for k, v in symptoms_map.items() if k in complain)
        symptom_score = clamp(symptom_score, 0, 1)

        image_score = 0.25 if (file and file.filename != "") else 0.0

        score = clamp((lab_score * 0.5 + symptom_score * 0.3 + image_score * 0.2), 0, 1)
        confidence = round(score * 100, 2)

        if score < 0.30:
            risk, advice = "LOW", "Normal findings. Routine follow-up recommended."
        elif score < 0.55:
            risk, advice = "MODERATE", "Mild abnormalities detected. Endocrinology consultation recommended."
        elif score < 0.80:
            risk, advice = "HIGH", "Significant abnormalities detected. Further diagnostic evaluation required."
        else:
            risk, advice = "CRITICAL", "Severe risk detected. Immediate medical attention required."

        # Твоят първи блок логика за Quiz интеграция към анализа:
        available_questions = [q for q in quiz_bank if q["question"] not in used_questions]
        if not available_questions:
            used_questions.clear()
            available_questions = quiz_bank

        quiz = random.choice(available_questions)
        used_questions.add(quiz["question"])

        options = quiz["options"].copy()
        random.shuffle(options)
        answer_index = options.index(quiz["correct"])

        return jsonify({
            "success": True,
            "status": "OK",
            "prediction": "Thyroid Risk Analysis",
            "confidence": confidence,
            "risk": risk,
            "follow_up": advice,
            "lab_score": round(lab_score, 2),
            "symptom_score": round(symptom_score, 2),
            "image_score": round(image_score, 2),
            "quiz": {
                "question": quiz["question"],
                "options": options,
                "answer": answer_index
            }
        })

    except Exception as e:
        return jsonify({"status": "ERROR", "success": False, "error": str(e), "risk": "LOW"}), 500