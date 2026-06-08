let riskChartInstance = null;
let confChartInstance = null;
async function loadStats() {
    try {
        const res = await fetch("/doctor/stats-data");
        const data = await res.json();
        if (!data || data.length === 0) {
            console.log("No data available");
            return;
        }
        let critical = 0;
        let normal = 0;
        let suspicious = 0;
        let sum = 0;
        data.forEach(r => {
            sum += Number(r.confidence || 0);
            if ((r.prediction || "").toLowerCase() === "critical")
                critical++;
            else if ((r.prediction || "").toLowerCase() === "normal")
                normal++;
            else
                suspicious++;
        });
        const avg = data.length
            ? (sum / data.length).toFixed(1)
            : 0;
        // ======================
        // UPDATE TOP CARDS
        // ======================
        document.getElementById("totalCases").innerText = data.length;
        document.getElementById("criticalCases").innerText = critical;
        document.getElementById("avgConfidence").innerText = avg + "%";
        document.getElementById("normalCases").innerText = normal;
        // ======================
        // DESTROY OLD CHARTS
        // ======================
        if (riskChartInstance)
            riskChartInstance.destroy();
        if (confChartInstance)
            confChartInstance.destroy();
        // ======================
        // PIE CHART
        // ======================
        riskChartInstance = new Chart(
            document.getElementById("riskChart"),
            {
                type: "doughnut",
                data: {
                    labels: [
                        "Critical",
                        "Normal",
                        "Suspicious"
                    ],
                    datasets: [{
                        data: [
                            critical,
                            normal,
                            suspicious
                        ],
                        backgroundColor: [
                            "#ef4444",
                            "#22c55e",
                            "#f59e0b"
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    plugins: {
                        legend: {
                            labels: {
                                color: "white"
                            },
                            position: "bottom"
                        }
                    }
                }
            }
        );
        // ======================
        // BAR CHART
        // ======================
        confChartInstance = new Chart(
            document.getElementById("confChart"),
            {
                type: "bar",
                data: {
                    labels: ["Average Confidence"],
                    datasets: [{
                        label: "Confidence %",
                        data: [avg],
                        backgroundColor: "#3b82f6",
                        borderRadius: 12
                    }]
                },
                options: {
                    plugins: {
                        legend: {
                            labels: {
                                color: "white"
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                color: "#cbd5e1"
                            },
                            grid: {
                                color: "rgba(255,255,255,0.06)"
                            }
                        },
                        x: {
                            ticks: {
                                color: "#cbd5e1"
                            },
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            }
        );
    } catch (err) {
        console.error("Stats error:", err);
    }
}
loadStats();
