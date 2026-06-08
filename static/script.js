// =====================================================
// GLOBAL VARIABLES
// =====================================================

let uploadedFile = null;
let historyData = [];

// =====================================================
// IMAGE PREVIEW
// =====================================================

function previewImage(input) {

    if (input.files && input.files[0]) {

        console.log("SELECTED FILE:", input.files[0]);

        document.getElementById("fileName").innerText =
            input.files[0].name;

        const reader = new FileReader();

        reader.onload = function(e) {

            document.getElementById("preview-image").src =
                e.target.result;

            document.getElementById("preview-image").style.display =
                "block";

            document.getElementById("scanned-image").src =
                e.target.result;

        }

        reader.readAsDataURL(input.files[0]);

    }

}

// =====================================================
// SHOW SECTION
// =====================================================

function showSection(section) {

    document.querySelectorAll('.content-section').forEach(sec => {
        sec.style.display = 'none';
    });

    document.getElementById(section + '-section').style.display = 'block';

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // FIX: add active state
    event.target.classList.add('active');
}

// =====================================================
// PROCESS ANALYSIS
// =====================================================

async function processAnalysis() {

    const fileInput = document.getElementById("fileInput");

    console.log("INPUT:", fileInput);
    console.log("FILES:", fileInput.files);

    if (!fileInput.files || fileInput.files.length === 0) {

        alert("Моля качете изображение.");
        return;

    }

    document.getElementById("loader").style.display = "block";

    const formData = new FormData();

    // ВАЖНО:
    formData.append("file", fileInput.files[0]);

    try {

        const response = await fetch("/predict", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        console.log("SERVER RESPONSE:", data);

        document.getElementById("loader").style.display = "none";

        if (data.success) {

            document.getElementById("results-area").style.display = "grid";

            document.getElementById("res-status").innerText =
                data.prediction;

            document.getElementById("res-conf").innerText =
                data.confidence + "%";

            document.getElementById("res-advice").innerText =
                data.advice;

            document.getElementById("ai-explanation").innerText =
                data.explanation;

            if (data.heatmap_url) {

                document.getElementById("heatmap-result").src =
                    data.heatmap_url;

            }

            // =========================
            // RISK
            // =========================

            const badge =
                document.getElementById("severity-badge");

            badge.innerText = data.risk_level;

            if (data.risk_level === "HIGH") {

                badge.style.background =
                    "rgba(255,0,0,0.2)";

                badge.style.color = "#ff4d4d";

            }
            else if (data.risk_level === "MODERATE") {

                badge.style.background =
                    "rgba(255,165,0,0.2)";

                badge.style.color = "#ffb347";

            }
            else {

                badge.style.background =
                    "rgba(0,255,100,0.2)";

                badge.style.color = "#4dff88";

            }

        }
        else {

            alert("AI Error: " + data.error);

        }

    }
    catch(err) {

        console.error(err);

        document.getElementById("loader").style.display =
            "none";

        alert("Server connection error.");

    }

}

// =====================================================
// GENERATE AI RESULT
// =====================================================

function generateFakeAIResult() {

    const statuses = [
        "Normal",
        "Suspicious",
        "Critical"
    ];

    const randomStatus =
        statuses[Math.floor(Math.random() * statuses.length)];

    const confidence =
        Math.floor(Math.random() * 30) + 70;

    let advice = "";
    let severityClass = "";
    let explanation = "";

    // =====================================================
    // RESULT LOGIC
    // =====================================================

    if (randomStatus === "Normal") {

        advice =
            "Няма сериозни отклонения. Препоръчва се стандартно проследяване.";

        severityClass = "risk-low";

        explanation =
            "AI моделът не откри значителни аномалии в сканирането.";

    }

    else if (randomStatus === "Suspicious") {

        advice =
            "Открити са съмнителни области. Препоръчва се допълнителен преглед.";

        severityClass = "risk-moderate";

        explanation =
            "AI откри потенциални изменения с умерен риск.";

    }

    else {

        advice =
            "Открит е висок риск. Необходима е консултация със специалист.";

        severityClass = "risk-high";

        explanation =
            "AI моделът идентифицира критични области с висока вероятност за патология.";
    }

    // =====================================================
    // DISPLAY RESULTS
    // =====================================================

    document.getElementById("loader").style.display = "none";

    document.getElementById("results-area").style.display = "grid";

    // IMAGE
    const previewSrc =
        document.getElementById("preview-image").src;

    document.getElementById("scanned-image").src = previewSrc;

    // HEATMAP
    document.getElementById("heatmap-result").src = previewSrc;

    // STATUS
    document.getElementById("res-status").innerText = randomStatus;

    // CONFIDENCE
    document.getElementById("res-conf").innerText =
        confidence + "%";

    document.getElementById("confidence-fill").style.width =
        confidence + "%";

    // ADVICE
    document.getElementById("res-advice").innerText = advice;

    // AI EXPLANATION
    document.getElementById("ai-explanation").innerText =
        explanation;

    // SEVERITY BADGE
    const badge = document.getElementById("severity-badge");

    badge.className = "severity-badge " + severityClass;

    badge.innerText = randomStatus.toUpperCase();

    // TIMELINE
    generateTimeline(randomStatus);

    // SAVE HISTORY
    saveHistory(randomStatus, confidence);

    // UPDATE DASHBOARD
    updateDashboard();
}

// =====================================================
// TIMELINE
// =====================================================

function generateTimeline(status) {

    const container =
        document.getElementById("timeline-container");

    container.innerHTML = "";

    const events = [
        {
            date: "08:30",
            text: "Качено медицинско изображение"
        },
        {
            date: "08:31",
            text: "AI обработка на сканирането"
        },
        {
            date: "08:32",
            text: "Генерирана диагноза: " + status
        }
    ];

    events.forEach(event => {

        container.innerHTML += `
            <div class="timeline-item">
                <div class="timeline-dot"></div>

                <div class="timeline-content">
                    <h4>${event.text}</h4>

                    <div class="timeline-date">
                        ${event.date}
                    </div>
                </div>
            </div>
        `;
    });
}

// =====================================================
// SAVE HISTORY
// =====================================================

function saveHistory(status, confidence) {

    const patientName =
        window.currentUser || "Patient";

    const today =
        new Date().toLocaleDateString("bg-BG");

    const historyItem = {
        patient: patientName,
        diagnosis: status,
        confidence: confidence,
        date: today
    };

    historyData.unshift(historyItem);

    localStorage.setItem(
        "medai_history",
        JSON.stringify(historyData)
    );

    renderHistory();
}

// =====================================================
// LOAD HISTORY
// =====================================================

function loadHistory() {

    const saved =
        localStorage.getItem("medai_history");

    if (saved) {

        historyData = JSON.parse(saved);

        renderHistory();
    }
}

// =====================================================
// RENDER HISTORY
// =====================================================

function renderHistory() {

    const tbody =
        document.getElementById("historyBody");

    const dashboardBody =
        document.getElementById("dashboardHistoryBody");

    if (!tbody || !dashboardBody) return;

    tbody.innerHTML = "";
    dashboardBody.innerHTML = "";

    historyData.forEach(item => {

        // HISTORY TABLE
        tbody.innerHTML += `
            <tr>
                <td>${item.patient}</td>
                <td>${item.diagnosis}</td>
                <td>${item.confidence}%</td>
                <td>${item.date}</td>
            </tr>
        `;

        // DASHBOARD TABLE
        dashboardBody.innerHTML += `
            <tr>
                <td>${item.patient}</td>
                <td>${item.diagnosis}</td>
                <td>
                    <div class="conf-bar-bg">
                        <div class="conf-bar-fill"
                             style="width:${item.confidence}%">
                        </div>
                    </div>

                    ${item.confidence}%
                </td>

                <td>
                    <span class="
                        risk-label
                        ${getRiskClass(item.diagnosis)}
                    ">
                        ${item.diagnosis}
                    </span>
                </td>

                <td>${item.date}</td>
            </tr>
        `;
    });
}

// =====================================================
// GET RISK CLASS
// =====================================================

function getRiskClass(status) {

    if (status === "Critical") return "risk-high";
    if (status === "Suspicious") return "risk-moderate";
    return "risk-low";
}
// =====================================================
// DASHBOARD STATS
// =====================================================

function updateDashboard() {

    let high = 0;
    let moderate = 0;
    let low = 0;

    historyData.forEach(item => {

        if (item.diagnosis === "Critical")
            high++;

        else if (item.diagnosis === "Suspicious")
            moderate++;

        else
            low++;
    });

    document.getElementById("highRiskCount").innerText =
        high;

    document.getElementById("moderateRiskCount").innerText =
        moderate;

    document.getElementById("lowRiskCount").innerText =
        low;

    document.getElementById("totalPatients").innerText =
        historyData.length;

    generateCharts(high, moderate, low);
}

// =====================================================
// CHARTS
// =====================================================

let pieChart = null;
let lineChart = null;

function generateCharts(high, moderate, low) {

    // PIE CHART
    const pieCtx =
        document.getElementById("riskPieChart");

    if (pieCtx) {

        if (pieChart)
            pieChart.destroy();

        pieChart = new Chart(pieCtx, {

            type: "doughnut",

            data: {
                labels: [
                    "Critical",
                    "Suspicious",
                    "Normal"
                ],

                datasets: [{
                    data: [high, moderate, low],
                    backgroundColor: [
                        "#ef4444",
                        "#f59e0b",
                        "#22c55e"
                    ]
                }]
            }
        });
    }

    // LINE CHART
    const lineCtx =
        document.getElementById("activityLineChart");

    if (lineCtx) {

        if (lineChart)
            lineChart.destroy();

        lineChart = new Chart(lineCtx, {

            type: "line",

            data: {

                labels: [
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun"
                ],

                datasets: [{
                    label: "AI Analyses",

                    data: [
                        4,
                        7,
                        10,
                        6,
                        12,
                        historyData.length
                    ],

                    borderColor: "#1976d2",

                    backgroundColor:
                        "rgba(25,118,210,0.1)",

                    tension: 0.4,

                    fill: true
                }]
            }
        });
    }
}

// =====================================================
// FILTER DASHBOARD
// =====================================================

function filterDashboard() {

    const search =
        document.getElementById("searchPatient")
            .value
            .toLowerCase();

    const filter =
        document.getElementById("filterPrediction")
            .value;

    const rows =
        document.querySelectorAll(
            "#dashboardHistoryBody tr"
        );

    rows.forEach(row => {

        const patient =
            row.children[0].innerText.toLowerCase();

        const diagnosis =
            row.children[1].innerText;

        const matchSearch =
            patient.includes(search);

        const matchFilter =
            filter === "" || diagnosis === filter;

        row.style.display =
            (matchSearch && matchFilter)
            ? ""
            : "none";
    });
}

// =====================================================
// EXPORT PDF
// =====================================================

function exportPDF() {

    const diagnosis =
        document.getElementById("res-status").innerText;

    const confidence =
        document.getElementById("res-conf").innerText;

    const advice =
        document.getElementById("res-advice").innerText;

    const docDefinition = {

        content: [

            {
                text: "MED-AI Medical Report",
                style: "header"
            },

            {
                text: "\n"
            },

            {
                text: "Diagnosis: " + diagnosis
            },

            {
                text: "Confidence: " + confidence
            },

            {
                text: "Advice: " + advice
            }
        ],

        styles: {

            header: {

                fontSize: 22,
                bold: true,
                color: "#1976d2"
            }
        }
    };

    pdfMake
        .createPdf(docDefinition)
        .download("medical_report.pdf");
}

// =====================================================
// INIT
// =====================================================

document.addEventListener("DOMContentLoaded", () => {

    loadHistory();

    updateDashboard();
});