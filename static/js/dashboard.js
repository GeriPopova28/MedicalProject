let allPatientsData = [];

document.addEventListener("DOMContentLoaded", () => {
    loadData();
    startAutoRefresh();
});

function loadData() {
    const data = window.dashboardData || [];
    initDashboard(data);
}

function initDashboard(data) {
    allPatientsData = Array.isArray(data) ? data : [];

    const search = document.getElementById("searchPatient");
    const filter = document.getElementById("filterPrediction");

    if (search) search.oninput = filterAndRender;
    if (filter) filter.onchange = filterAndRender;

    filterAndRender();
}

/* ================= FILTER ================= */

function filterAndRender() {
    const searchQuery =
        (document.getElementById("searchPatient")?.value || "").toLowerCase();

    const filterValue =
        document.getElementById("filterPrediction")?.value || "";

    const filtered = allPatientsData.filter(p => {
        const name = (p.name || "").toLowerCase();
        const status = getStatus(p);

        return name.includes(searchQuery) &&
            (!filterValue || status === filterValue);
    });

    updateCounters(filtered);
    renderTable(filtered);
}

/* ================= STATUS ================= */

function getStatus(p) {
    return p?.status || p?.diagnosis || "Normal";
}

/* ================= COUNTERS ================= */

function updateCounters(data) {
    let c = 0, s = 0, n = 0;

    data.forEach(p => {
        const status = getStatus(p);

        if (status === "Critical") c++;
        else if (status === "Suspicious") s++;
        else n++;
    });

    setText("highRiskCount", c);
    setText("moderateRiskCount", s);
    setText("lowRiskCount", n);
    setText("totalPatients", data.length);
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value;
}

/* ================= TABLE ================= */

function renderTable(data) {
    const tbody = document.getElementById("dashboardHistoryBody");
    if (!tbody) return;

    tbody.innerHTML = data.map(p => {
        const status = getStatus(p);

        return `
            <tr>
                <td>${p.name || "-"}</td>
                <td>${status}</td>
                <td>${p.confidence ?? 0}%</td>
                <td>${p.risk || "-"}</td>
                <td>${p.date || "-"}</td>
            </tr>
        `;
    }).join("");
}

/* ================= AUTO REFRESH ================= */

function startAutoRefresh() {
    setInterval(async () => {
        try {
            console.log("Fetching...");

            const res = await fetch("/api/dashboard-data");

            if (!res.ok) {
                console.error("API error:", res.status);
                return;
            }

            const data = await res.json();

            console.log("NEW DATA:", data);

            allPatientsData = data || [];
            filterAndRender();

        } catch (err) {
            console.error("Fetch failed:", err);
        }
    }, 5000);
}