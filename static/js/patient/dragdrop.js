document.addEventListener("DOMContentLoaded", () => {

    const dropzone = document.getElementById("dropzone");

    if (!dropzone) return;

    ["dragenter", "dragover"].forEach(evt => {
        dropzone.addEventListener(evt, e => {
            e.preventDefault();
            dropzone.style.borderColor = "#38bdf8";
        });
    });

    ["dragleave", "drop"].forEach(evt => {
        dropzone.addEventListener(evt, e => {
            e.preventDefault();
            dropzone.style.borderColor = "rgba(56, 189, 248, 0.3)";
        });
    });

    dropzone.addEventListener("drop", e => {
        const files = e.dataTransfer.files;
        if (files.length) {
            document.getElementById("fileInput").files = files;
            previewImage(document.getElementById("fileInput"));
        }
    });

});