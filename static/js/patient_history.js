let allData = [];
let initialized = false;


// Помощна функция за форматиране на датата от MySQL формат
function formatDate(dateStr) {
    if (!dateStr) return "-";
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleString('bg-BG', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch(e) {
        return dateStr;
    }
}


async function loadHistory() {
    try {
        const res = await fetch("/patient-data?ts=" + Date.now());
        allData = await res.json();


        updateStats(allData);
       
        // Прилагаме филтрите след зареждане, за да не нулираме търсенето на потребителя
        applyFilters();


    } catch (err) {
        console.error("Error loading history:", err);
    }
}


function updateStats(data){
    document.getElementById("totalAnalyses").innerText = data.length;


    if(data.length > 0){
        document.getElementById("lastPrediction").innerText = data[0].prediction || "-";
        document.getElementById("lastRisk").innerText = data[0].risk_level || "-";
       
        // Динамичен цвят на риска в статистическата карта
        const risk = (data[0].risk_level || "").toLowerCase();
        document.getElementById("lastRisk").className = (risk === "low" || risk === "high" || risk === "critical") ? risk : "moderate";
    } else {
        document.getElementById("lastPrediction").innerText = "-";
        document.getElementById("lastRisk").innerText = "-";
        document.getElementById("lastRisk").className = "";
    }
}

function renderTable(data){
    const table = document.getElementById("historyTable");
    table.innerHTML = "";

    if(data.length === 0){
        table.innerHTML = `
            <tr>
                <td colspan="6" style="text-align:center; opacity:0.7; padding:30px;">
                    Няма налични AI анализи
                </td>
            </tr>
        `;
        return;
    }
    
    let tableHtml = ""; 
    data.forEach((item, index) => {
        let riskClass = "moderate";
        const r = String(item.risk_level).toUpperCase();
        if(r === "LOW") riskClass = "low";
        else if(r === "HIGH") riskClass = "high";
        else if(r === "CRITICAL") riskClass = "critical";

        let aiClassColor = "";
        if(item.ai_class === "Benign") aiClassColor = "green";
        else if(item.ai_class === "Malignant") aiClassColor = "red";
        else if(item.ai_class === "Uncertain") aiClassColor = "orange";

        const formattedDate = formatDate(item.created_at);
        const explanationText = 
            item.explanation && item.explanation.trim()
            ? item.explanation
            : "Няма допълнителен текстов отчет за този анализ.";

        tableHtml += `
            <tr class="main-row">
                <td>${formattedDate}</td>
                <td style="font-weight: 500;">${item.prediction || "-"}</td>
                <td>${item.confidence || "0"}%</td>
                <td style="color:${aiClassColor}; font-weight:600;">
                    ${item.ai_class || "-"}
                </td>
                <td class="${riskClass}">${r || "-"}</td>
                <td style="text-align: center;">
                    <button class="btn-toggle-details" onclick="toggleDetails(${index})">Виж отчет</button>
                </td>
            </tr>
            <tr id="details-${index}" class="details-row" style="display: none;">
                <td colspan="6">
                    <div class="details-box">
                        ${explanationText}
                    </div>
                </td>
            </tr>
        `;
    });

    table.innerHTML = tableHtml;
}

// Функция за разгъване и свиване на медицинския отчет
function toggleDetails(index) {
    const row = document.getElementById(`details-${index}`);
    if (row.style.display === "none") {
        row.style.display = "table-row";
    } else {
        row.style.display = "none";
    }
}


function applyFilters(){
    let search = document.getElementById("searchInput").value.toLowerCase();
    let risk = document.getElementById("riskFilter").value;


    let filtered = allData.filter(item => {
        let matchSearch =
            (item.prediction || "").toLowerCase().includes(search) ||
            (item.created_at || "").toLowerCase().includes(search);


        let matchRisk =
            risk === "" || String(item.risk_level).toUpperCase() === risk;


        return matchSearch && matchRisk;
    });


    renderTable(filtered);
}


function initHistoryPage(){
    if(initialized) return;
    initialized = true;


    document.getElementById("searchInput").addEventListener("input", applyFilters);
    document.getElementById("riskFilter").addEventListener("change", applyFilters);


    loadHistory();
    setInterval(() => loadHistory(), 15000);
}

window.addEventListener("storage", (e) => {
    if (e.key === "ai_refresh") {
        loadHistory();
    }
});

document.addEventListener("DOMContentLoaded", initHistoryPage);
window.addEventListener("historyUpdate", loadHistory);
