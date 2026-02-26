(function () {
    "use strict";

    const form = document.getElementById("uploadForm");
    const fileInput = document.getElementById("fileInput");
    const fileUploadArea = document.getElementById("fileUploadArea");
    const fileNameEl = document.getElementById("fileName");
    const submitBtn = document.getElementById("submitBtn");
    const btnText = submitBtn.querySelector(".btn-text");
    const btnLoader = document.getElementById("btnLoader");
    const progressSection = document.getElementById("progressSection");
    const progressFill = document.getElementById("progressFill");
    const progressPercentage = document.getElementById("progressPercentage");
    const progressMessage = document.getElementById("progressMessage");
    const resultSection = document.getElementById("resultSection");
    const downloadBtn = document.getElementById("downloadBtn");
    const errorSection = document.getElementById("errorSection");
    const errorMessage = document.getElementById("errorMessage");

    const ALLOWED = ["mp4", "mov", "avi", "mkv", "webm", "m4v"];

    function isVideoFile(name) {
        const ext = (name || "").split(".").pop().toLowerCase();
        return ALLOWED.includes(ext);
    }

    function setFile(name) {
        fileNameEl.textContent = name || "";
        submitBtn.disabled = !name;
    }

    fileUploadArea.addEventListener("click", function () {
        fileInput.click();
    });

    fileInput.addEventListener("change", function () {
        const f = fileInput.files[0];
        if (f && isVideoFile(f.name)) setFile(f.name);
        else setFile("");
    });

    fileUploadArea.addEventListener("dragover", function (e) {
        e.preventDefault();
        e.stopPropagation();
        fileUploadArea.classList.add("dragover");
    });

    fileUploadArea.addEventListener("dragleave", function () {
        fileUploadArea.classList.remove("dragover");
    });

    fileUploadArea.addEventListener("drop", function (e) {
        e.preventDefault();
        e.stopPropagation();
        fileUploadArea.classList.remove("dragover");
        const f = e.dataTransfer.files[0];
        if (f && isVideoFile(f.name)) {
            fileInput.files = e.dataTransfer.files;
            setFile(f.name);
        } else {
            setFile("");
        }
    });

    function showProgress() {
        progressSection.style.display = "block";
        resultSection.style.display = "none";
        errorSection.style.display = "none";
    }

    function showResult(downloadUrl) {
        progressSection.style.display = "none";
        resultSection.style.display = "block";
        errorSection.style.display = "none";
        downloadBtn.href = downloadUrl;
    }

    function showError(msg) {
        progressSection.style.display = "none";
        resultSection.style.display = "none";
        errorSection.style.display = "block";
        errorMessage.textContent = msg;
    }

    function pollProgress(jobId) {
        fetch("/progress/" + jobId)
            .then(function (r) {
                if (!r.ok) throw new Error("Progress request failed");
                return r.json();
            })
            .then(function (data) {
                const pct = data.progress || 0;
                progressFill.style.width = pct + "%";
                progressPercentage.textContent = pct + "%";
                progressMessage.textContent = data.message || "";

                if (data.status === "done") {
                    submitBtn.disabled = false;
                    btnText.style.display = "";
                    btnLoader.style.display = "none";
                    showResult("/download/" + jobId);
                    return;
                }
                if (data.status === "error") {
                    submitBtn.disabled = false;
                    btnText.style.display = "";
                    btnLoader.style.display = "none";
                    showError(data.message || "Unknown error");
                    return;
                }
                setTimeout(function () {
                    pollProgress(jobId);
                }, 600);
            })
            .catch(function (err) {
                submitBtn.disabled = false;
                btnText.style.display = "";
                btnLoader.style.display = "none";
                showError(err.message || "Network error");
            });
    }

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        const f = fileInput.files[0];
        if (!f || !isVideoFile(f.name)) return;

        const fd = new FormData();
        fd.append("file", f);
        fd.append("model_name", document.getElementById("modelSelect").value);
        fd.append("shifts", document.getElementById("qualitySelect").value);

        submitBtn.disabled = true;
        btnText.style.display = "none";
        btnLoader.style.display = "inline-flex";
        showProgress();
        progressFill.style.width = "0%";
        progressPercentage.textContent = "0%";
        progressMessage.textContent = "Uploading…";

        fetch("/upload", {
            method: "POST",
            body: fd,
        })
            .then(function (r) {
                if (!r.ok) return r.json().then(function (d) {
                    throw new Error(d.error || "Upload failed");
                });
                return r.json();
            })
            .then(function (data) {
                progressMessage.textContent = "Starting…";
                pollProgress(data.job_id);
            })
            .catch(function (err) {
                submitBtn.disabled = false;
                btnText.style.display = "";
                btnLoader.style.display = "none";
                showError(err.message || "Upload failed");
            });
    });
})();
