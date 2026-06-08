function previewImage(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('dropzoneText').style.display = 'none';
            document.getElementById('imagePreviewContainer').style.display = 'flex';
            document.getElementById('imagePreview').src = e.target.result;
        }
        reader.readAsDataURL(input.files[0]);
    }
}
async function startAIAnalysis() {

    const fileInput = document.getElementById('fileInput');
    const complain = document.getElementById('complainInput').value;
    const tsh = document.getElementById('tshInput').value;
    const ft4 = document.getElementById('ft4Input').value;
    const mat = document.getElementById('matInput').value;
    const tat = document.getElementById('tatInput').value;

    const age = document.querySelector('input[name="age"]').value;
    const gender = document.querySelector('select[name="gender"]').value;

    const family_history = document.querySelector('input[name="family_history"]').checked;
    const previous_thyroid_disease = document.querySelector('input[name="previous_thyroid_disease"]').checked;
    const autoimmune_history = document.querySelector('input[name="autoimmune_history"]').checked;

    if (!fileInput.files[0]) {
        alert("Моля, качете ехографско изображение първо.");
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('complain', complain);
    formData.append('tsh', tsh);
    formData.append('ft4', ft4);
    formData.append('mat', mat);
    formData.append('tat', tat);

    formData.append('age', age);
    formData.append('gender', gender);

    if (family_history)
        formData.append('family_history', 'on');

    if (previous_thyroid_disease)
        formData.append('previous_thyroid_disease', 'on');

    if (autoimmune_history)
        formData.append('autoimmune_history', 'on');

    try {
        const btn = document.querySelector('.btn-analysis');
        btn.innerText = "Анализиране...";
        btn.disabled = true;

        const res = await fetch("/predict", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            throw new Error("Server error");
        }

        const data = await res.json();

        if (!data.success) {
            alert(data.error || "Грешка от сървъра");
            return;
        }

        // =========================
        // NOTIFY HISTORY PAGE
        // =========================
        localStorage.setItem("ai_refresh", Date.now());
        window.dispatchEvent(new Event("historyUpdate"));

        // =========================
        // BASIC RESULTS
        // =========================
        const confidence = Number(data.confidence ?? 0);

        document.getElementById('resStatus').innerText =
            data.status || "Normal Finding";

        document.getElementById('resConfidence').innerText =
            confidence + "%";

        const confElement = document.getElementById("resConfidence");
        confElement.className =
            confidence < 40 ? "value conf-low" :
            confidence < 70 ? "value conf-medium" :
            "value conf-high";

        document.getElementById("confidenceFill").style.width =
            confidence + "%";

        document.getElementById('resFollowUp').innerText =
            data.follow_up || "Няма специфични препоръки.";

        document.getElementById('resLab').innerText =
            data.lab_score ?? 0;

        document.getElementById('resSymptom').innerText =
            data.symptom_score ?? 0;

        document.getElementById('resImage').innerText =
            data.image_score ?? 0;

        // =========================
        // RISK
        // =========================
        const risk = (data.risk || "LOW").toUpperCase();

        const badge = document.getElementById('resRiskBadge');
        badge.innerText = risk;
        badge.className = risk.toLowerCase();

        // =========================
        // AI CLASS (IMPORTANT FIX)
        // =========================
        const aiClass = data.ai_class || "Unknown";
        const classEl = document.getElementById("resClass");

        classEl.innerText = aiClass;

        classEl.style.fontWeight = "700";

        if (aiClass === "Benign") classEl.style.color = "green";
        else if (aiClass === "Malignant") classEl.style.color = "red";
        else classEl.style.color = "orange";

        // =========================
        // EXPLANATION
        // =========================
        let whyAI = "";

        switch (risk) {
            case "LOW":
                whyAI = "Нисък клиничен риск. Показателите са в референтни граници и не се наблюдават значими отклонения.Препоръка: рутинен контрол (1x годишно)";
                break;
            case "MODERATE":
                whyAI = "Умерен риск.Наблюдават се начални отклонения в лабораторни или ехографски показатели. Симптомите могат да подсказват ранна дисфункция.Препоръка: контролен преглед в близките седмици.";
                break;
            case "HIGH":
                whyAI = "Висок риск. Отклонения в хормонални/автоимунни маркери + ехографски изменения. Симптомите са по-изразени. Препоръка: консултация с ендокринолог в следващите 2 седмици.";
                break;
            default:
                whyAI = "Анализът е завършен,  но класификацията е несигурна.AI моделът не е достатъчно уверен в резултата. Препоръка: повторно изследване или допълнителни данни за по-точна оценка.";
        }

        whyAI += "\n\n AI класификация: " + (data.ai_class || "-");
        whyAI += "\n AI увереност: " + (data.ai_confidence || 0) + "%";
        whyAI += "\n Benign: " + (data.benign_prob || 0);
        whyAI += "\n Malignant: " + (data.malignant_prob || 0);

        document.getElementById("resWhyAI").innerText = whyAI;

        // =========================
        // SHOW RESULT CARD
        // =========================
        document.getElementById('resultCard').style.display = 'block';

    } catch (err) {
        console.error(err);
        alert("Грешка при комуникацията със сървъра.");
    } finally {
        const btn = document.querySelector('.btn-analysis');
        btn.innerText = "Стартирай AI анализ";
        btn.disabled = false;
    }
}
// =========================
// DRAG & DROP SUPPORT
// =========================
const dropzone = document.getElementById('dropzone');
['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.style.borderColor = '#38bdf8';
    });
});
['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'rgba(56, 189, 248, 0.3)';
    });
});
dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        document.getElementById('fileInput').files = files;
        previewImage(document.getElementById('fileInput'));
    }
});
