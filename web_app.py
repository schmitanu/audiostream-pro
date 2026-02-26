"""
AudioStem-Pro — Web interface. Run with: python web_app.py
Opens the same workflow in the browser: upload video, progress, download result.

Author: Eduarth Schmidt
"""

__author__ = "Eduarth Schmidt"

import os
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from core.audio_utils import check_ffmpeg_available
from core.pipeline import DEMUCS_MODELS, QUALITY_PROFILES, run_pipeline

VALID_MODELS = {"htdemucs", "mdx_extra_q", "htdemucs_6s"}
VALID_SHIFTS = {s for s, _ in QUALITY_PROFILES}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()
app.config["UPLOAD_FOLDER"] = Path(__file__).resolve().parent / "uploads"
app.config["OUTPUT_FOLDER"] = Path(__file__).resolve().parent / "outputs"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024  # 2 GB

app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
app.config["OUTPUT_FOLDER"].mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm", "m4v"}
JOBS: dict[str, dict] = {}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html", models=DEMUCS_MODELS, quality_profiles=QUALITY_PROFILES)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "File type not allowed. Use .mp4, .mov, etc."}), 400

    filename = secure_filename(f.filename)
    filepath = app.config["UPLOAD_FOLDER"] / filename
    f.save(str(filepath))

    model_name = request.form.get("model_name", "htdemucs").strip()
    if model_name not in VALID_MODELS:
        model_name = "htdemucs"
    try:
        shifts = int(request.form.get("shifts", 1))
    except (TypeError, ValueError):
        shifts = 1
    if shifts not in VALID_SHIFTS:
        shifts = 1

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "starting",
        "progress": 0,
        "message": "Starting…",
        "output_path": None,
        "output_filename": None,
    }

    def run():
        try:
            def on_progress(msg: str, pct: int):
                JOBS[job_id]["message"] = msg
                JOBS[job_id]["progress"] = pct
                JOBS[job_id]["status"] = "running"

            out_path = run_pipeline(
                filepath,
                output_dir=app.config["OUTPUT_FOLDER"],
                progress_callback=on_progress,
                model_name=model_name,
                shifts=shifts,
            )
            JOBS[job_id]["status"] = "done"
            JOBS[job_id]["progress"] = 100
            JOBS[job_id]["message"] = "Done"
            JOBS[job_id]["output_path"] = str(out_path)
            JOBS[job_id]["output_filename"] = out_path.name
        except Exception as e:
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["message"] = str(e)
            JOBS[job_id]["progress"] = 0
        finally:
            try:
                filepath.unlink(missing_ok=True)
            except OSError:
                pass

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>")
def progress(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "Unknown job"}), 404
    j = JOBS[job_id]
    return jsonify({
        "status": j["status"],
        "progress": j["progress"],
        "message": j["message"],
        "output_filename": j.get("output_filename"),
    })


@app.route("/download/<job_id>")
def download(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "Unknown job"}), 404
    path = JOBS[job_id].get("output_path")
    if not path or not Path(path).exists():
        return jsonify({"error": "Output not ready or expired"}), 404
    filename = JOBS[job_id].get("output_filename") or Path(path).name
    return send_file(path, as_attachment=True, download_name=filename)


@app.route("/health")
def health():
    ffmpeg_ok, ffmpeg_msg = check_ffmpeg_available()
    return jsonify({"ffmpeg_ok": ffmpeg_ok, "ffmpeg_message": ffmpeg_msg})


def main():
    import webbrowser
    from threading import Timer

    port = int(os.environ.get("PORT", 5050))
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    def open_browser():
        webbrowser.open(url)

    Timer(1.2, open_browser).start()
    print(f"AudioStem-Pro web UI: {url}")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
