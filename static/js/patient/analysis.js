document.addEventListener("DOMContentLoaded", () => {

    document.getElementById("analyzeBtn").addEventListener("click", async () => {

        const fileInput = document.getElementById("fileInput");

        if (!fileInput.files[0]) {
            alert("Качи файл първо!");
            return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        formData.append("complain", document.getElementById("complainInput").value);
        formData.append("tsh", document.getElementById("tshInput").value);
        formData.append("ft4", document.getElementById("ft4Input").value);
        formData.append("mat", document.getElementById("matInput").value);
        formData.append("tat", document.getElementById("tatInput").value);

        try {
            const btn = document.getElementById("analyzeBtn");
            btn.innerText = "Анализ...";
            btn.disabled = true;

            const res = await fetch("/predict", {
                method: "POST",
                body: formData
            });

            const data = await res.json();

            if (!res.ok || data.success === false) {
                alert(data.error || "Server error");
                return;
            }

            // UI update
            document.getElementById("resultCard").style.display = "block";

            const conf = Number(data.confidence || 0);

            document.getElementById("resStatus").innerText = data.status;
            document.getElementById("resConfidence").innerText = conf + "%";
            document.getElementById("confidenceFill").style.width = conf + "%";

            const risk = (data.risk || "LOW").toLowerCase();
            const badge = document.getElementById("resRiskBadge");

            badge.innerText = risk.toUpperCase();
            badge.className = risk;

        } catch (e) {
            console.error(e);
            alert("Грешка при комуникация със сървъра");
        } finally {
            const btn = document.getElementById("analyzeBtn");
            btn.innerText = "Стартирай AI анализ";
            btn.disabled = false;
        }
    });
});