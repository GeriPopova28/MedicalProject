let globalData = [];


// =========================
// LOAD DATA FROM API
// =========================
async function loadPatients() {
    try {
        const res = await fetch("/doctor/stats-data");
        const data = await res.json();


        console.log("DATA RECEIVED:", data);


        if (!Array.isArray(data)) {
            document.getElementById("patients").innerHTML =
                "<tr><td colspan='7' style='text-align:center; color:#f87171;'>Възникна грешка при обработката на данните.</td></tr>";
            return;
        }


        globalData = data;
        renderTable(globalData);


    } catch (err) {
        console.error("Грешка при зареждане:", err);
        document.getElementById("patients").innerHTML =
            "<tr><td colspan='7' style='text-align:center; color:#f87171;'>Грешка при връзката със сървъра.</td></tr>";
    }
}


// =========================
// RENDER DYNAMIC TABLE
// =========================
function renderTable(data) {
    const tableBody = document.getElementById("patients");

    if (!data.length) {
        tableBody.innerHTML =
            "<tr><td colspan='7' style='text-align:center; color:#94a3b8;'>Няма намерени медицински досиета.</td></tr>";
        return;
    }

    let html = "";

    data.forEach(p => {
        const id = p.id || index;
        const risk = (p.risk_level || "LOW").toUpperCase();

        let riskClass = "risk-low";
        if (risk === "HIGH" || risk === "ВИСОК") riskClass = "risk-high";
        if (risk === "MEDIUM" || risk === "СРЕДЕН") riskClass = "risk-medium";

        html += `
            <tr>
                <td><span style="color:#ffffff; font-weight:600;">${p.patient_name ?? "-"}</span></td>
                <td><span style="color:#93c5fd;">${p.prediction ?? "-"}</span></td>
                <td><b style="color:#34d399;">${p.confidence ?? 0}%</b></td>
                <td><span class="badge-risk ${riskClass}">${risk}</span></td>
                <td>${p.advice ?? "-"}</td>
                <td style="color:#94a3b8; font-size:13px;">${p.created_at ?? "-"}</td>
                <td>
                    <button class="btn-toggle-report" onclick="toggleReport(${id})">
                        <i class="far fa-folder-open"></i> Преглед
                    </button>
                </td>
            </tr>

            <tr id="report-${id}" class="report-row" style="display:none;">
                <td colspan="7">
                    <div class="report-box">
                        <h3>Детайлен клиничен отчет</h3>
                        <textarea 
                            id="edit-${id}"
                            style="
                                width:100%;
                                min-height:120px;
                                padding:10px;
                                border-radius:10px;
                                background:#0f172a;
                                color:white;
                                border:1px solid #334155;
                                margin-top:10px;
                            "
                        >${p.explanation ?? ""}</textarea>

                        <div style="margin-top:20px; display:flex; gap:12px;">
                            <button class="btn-pdf" onclick="generatePDF(${id})">
                                Generate PDF
                            </button>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    });

    tableBody.innerHTML = html;
}


// =========================
// TOGGLE EXPANDABLE ROW
// =========================
function toggleReport(id) {
    const row = document.getElementById(`report-${id}`);
    if (!row) return;

    if (row.style.display === "none" || row.style.display === "") {
        row.style.display = "table-row";
    } else {
        row.style.display = "none";
    }
}

async function generatePDF(id) {

    const explanation = document.getElementById(`edit-${id}`).value;

    const res = await fetch(`/doctor/generate-pdf/${id}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            explanation: explanation
        })
    });

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    window.open(url);
}


// =========================
// ACTION INTERACTION
// =========================
async function sendDecision(id, decision) {
    try {
        const res = await fetch("/doctor/diagnosis-decision", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                analysis_id: Number(id),
                decision: decision
            })
        });


        const data = await res.json();


        if (data.success) {
            alert("Статусът на експертизата е актуализиран успешно.");
           
            // Отваряне на генерирания PDF в нов раздел
            window.open(`/doctor/generate-pdf/${id}`, "_blank");
            loadPatients();
        } else {
            alert(data.error || "Възникна системна грешка.");
        }


    } catch (err) {
        console.error(err);
        alert("Грешка при комуникация със сървъра.");
    }
}


function confirmDiagnosis(id) { sendDecision(id, "confirmed"); }
function rejectDiagnosis(id) { sendDecision(id, "rejected"); }


// =========================
// UTILS: SORTING
// =========================
function sortByConfidence() {
    globalData.sort((a,b) => (b.confidence || 0) - (a.confidence || 0));
    renderTable(globalData);
}


document.addEventListener("DOMContentLoaded", () => {
    // Безопасно закачане на търсачката чак след пълен лоуд на DOM дървото
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        searchInput.addEventListener("input", e => {
            const query = e.target.value.toLowerCase();
            const filtered = globalData.filter(p =>
                (p.patient_name || "").toLowerCase().includes(query) ||
                (p.prediction || "").toLowerCase().includes(query)
            );
            renderTable(filtered);
        });
    }
    // Първоначално извикване
    loadPatients();
});


function sortByDate() {
    globalData.sort((a,b) => new Date(b.created_at) - new Date(a.created_at));
    renderTable(globalData);
}
