let currentQuestion = 0;
let totalQuestions = 10;

let correctCount = 0;
let wrongCount = 0;

let lastAnswer = null;

// START
window.onload = () => {
    document.getElementById("quiz").innerHTML = `
        <button id="start-btn" onclick="loadQuiz()">
            Започни теста!
        </button>
    `;
};

// LOAD QUESTION
// LOAD QUESTION
async function loadQuiz(){

    document.getElementById("loader").style.display = "block";
    document.getElementById("result").style.display = "none";

    try{
        // Взимаме последните данни на пациента от localStorage (записани при предишен анализ/качване)
        const savedData = JSON.parse(localStorage.getItem("last_analysis")) || {};
        const labData = savedData.lab_data || { tsh: 0.0, ft4: 0.0 }; 
        const symptomsList = savedData.symptoms || "няма въведени симптоми";

        const res = await fetch("/generate_ai_quiz", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                lab_data: labData,
                symptoms: symptomsList,
                history: []
            })
        });

        const data = await res.json();

        document.getElementById("loader").style.display = "none";

        if(!data.success || !data.quiz){
            showError(data.error || "AI quiz failed");
            return;
        }

        const q = data.quiz;
        lastAnswer = Number(q.answer);

        let html = `
            <div class="question-box">
                <h3>${q.question}</h3>
            </div>
        `;

        q.options.forEach((opt,i)=>{
            html += `
                <label class="option">
                    <input type="radio" name="quiz" value="${i}">
                    <span>${opt}</span>
                </label>
            `;
        });

        html += `
            <button id="check-btn" onclick="checkAnswer()">✔ Провери</button>
            <button id="next-btn" onclick="nextQuestion()" style="display:none;">Следващ</button>
        `;

        document.getElementById("quiz").innerHTML = html;

        updateProgress();

    }catch(err){
        document.getElementById("loader").style.display = "none";
        showError("Грешка при връзка със сървъра");
    }
}

// CHECK
function checkAnswer(){

    const selected = document.querySelector('input[name="quiz"]:checked');

    if(!selected){
        showError("Избери отговор");
        return;
    }

    const userAnswer = Number(selected.value);

    document.querySelectorAll('input[name="quiz"]').forEach(el => el.disabled = true);

    document.getElementById("check-btn").style.display = "none";
    document.getElementById("next-btn").style.display = "block";

    const result = document.getElementById("result");
    result.style.display = "block";

    if(userAnswer === lastAnswer){
        correctCount++;
        result.className = "result-box success";
        result.innerHTML = "✔ Вярно";
    }else{
        wrongCount++;
        result.className = "result-box error";
        result.innerHTML = `Грешно. Отговор: ${lastAnswer + 1}`;
    }
}

// NEXT
function nextQuestion(){

    currentQuestion++;

    if(currentQuestion >= totalQuestions){
        showFinal();
        return;
    }

    loadQuiz();
}

// FINAL
function showFinal(){

    const percent = Math.round((correctCount / totalQuestions) * 100);

    document.getElementById("quiz").innerHTML = `
        <h2>Завършено</h2>
        <div class="final-score">${percent}%</div>
    `;

    document.getElementById("progress-bar").style.width = "100%";
    document.getElementById("progress-text").innerText = "Done";
}

// PROGRESS
function updateProgress(){

    let percent = ((currentQuestion + 1) / totalQuestions) * 100;

    document.getElementById("progress-bar").style.width = percent + "%";

    document.getElementById("progress-text").innerText =
        `Question ${currentQuestion + 1} / ${totalQuestions}`;
}

// ERROR
function showError(msg){
    const result = document.getElementById("result");
    result.style.display = "block";
    result.className = "result-box error";
    result.innerHTML = msg;
}