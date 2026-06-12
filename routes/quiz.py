from flask import Blueprint, request, jsonify
import random
from utils.auth_helpers import is_logged_in

quiz_bp = Blueprint('quiz', __name__)

used_questions = set()


quiz_bank = [
    {
        "question": "Кой е основният хормон, стимулиращ щитовидната жлеза?",
        "options": ["TSH (Тиреотропен хормон)", "Инсулин", "Кортизол", "Адреналин"],
        "correct": "TSH (Тиреотропен хормон)"
    },
    {
        "id": 2,
        "question": "Кои антитела обикновено се изследват за доказване на Хашимото?",
        "options": ["MAT и TAT", "ANA", "Anti-ccp", "IgE"],
        "correct": "MAT и TAT"
    },
    {
        "question": "Кой симптом е най-характерен за Хипотиреоидизъм (намалена функция)?",
        "options": ["Постоянна умора и зиморничавост", "Рязко отслабване", "Прекомерно изпотяване", "Ускорен пулс"],
        "correct": "Постоянна умора и зиморничавост"
    },
    {
        "question": "Какво представлява Базедовата болест?",
        "options": ["Автоимунно състояние с хиперфункция", "Хроничен недостиг на калций", "Възпаление на панкреаса", "Рак на щитовидната жлеза"],
        "correct": "Автоимунно състояние с хиперфункция"
    }
]

@quiz_bp.route('/get-quiz-question', methods=['GET', 'POST'])
def get_quiz_question():
    try:
        # Проверка за логнат потребител
        if not is_logged_in():
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        data = request.get_json(silent=True) or {}
        diagnosis = data.get("diagnosis", "Няма налична нова диагноза")
        available_questions = [
            q for q in quiz_bank
            if q["question"] not in used_questions
        ]
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
            "diagnosis": diagnosis,
            "quiz": {
                "question": quiz["question"],
                "options": options,
                "answer": answer_index
            }
        })

    except Exception as e:
        print("QUIZ ERROR:", e)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500