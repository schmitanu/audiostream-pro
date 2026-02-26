# AudioStem-Pro

**Author:** [Eduarth Schmidt](https://aiautomationflows.com/)

A desktop application that extracts **background music** from video files by removing vocals using AI (Demucs **htdemucs** 4-stem model). Output is a single WAV file combining drums, bass, and other stems—no vocals.

---

## Features

- **Modern dark-themed UI** — PyQt6 desktop app with drag-and-drop and clear status
- **Video → background music** — Supports `.mp4`, `.mov`, and other common video formats
- **AI separation** — Uses Demucs `htdemucs` for 4-stem separation (vocals, drums, bass, other)
- **Single output** — Automatically combines drums + bass + other into `{original_name}_background_music.wav`
- **Non-blocking** — Processing runs in a background thread so the UI stays responsive
- **Open output folder** — Button appears after completion to open the output directory (desktop) or download the WAV (web)
- **Web UI** — Run in the browser with the same workflow: upload video, progress, download result (see **Run in browser** below)
- **Graceful errors** — Checks for FFmpeg at startup and reports extraction/separation failures clearly

---

## System requirements

- **OS**: macOS, Linux, or Windows
- **Python**: 3.9–3.12 (3.13 not yet fully supported by PyTorch)
- **RAM**: 8 GB+ recommended (Demucs and PyTorch are memory-heavy)
- **Disk**: ~2–4 GB free (PyTorch + Demucs model + temp files)
- **FFmpeg**: Must be installed and on `PATH` (see below)

---

## Dependencies

### System: FFmpeg

Audio is extracted from video using FFmpeg. Install it if missing:

| Platform | Command |
|----------|--------|
| **macOS** | `brew install ffmpeg` |
| **Windows** | `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html) |
| **Linux** | `sudo apt install ffmpeg` (Debian/Ubuntu) or equivalent |

The app shows a warning at startup if FFmpeg is not found.

### Python

All Python dependencies are in `requirements.txt`:

- **PyQt6** — Desktop UI
- **demucs** — AI source separation (htdemucs)
- **torch** / **torchaudio** — Demucs backend
- **ffmpeg-python** — Optional; the app uses `subprocess` to call FFmpeg directly. Kept in requirements for consistency with the requested stack and possible future use.
- **soundfile** — Used if we add fallback mixing from WAV files; Demucs API uses its own `save_audio`. Can keep for consistency.
- **numpy** — Required by Demucs/torch
- **flask** / **werkzeug** — Web UI (browser template)

---

## Installation

### 1. Clone or copy the project

Clone the repo or download the project to any folder on your machine (no other projects required):

```bash
git clone https://github.com/schmitanu/audiostream-pro.git
cd audiostream-pro
```

### 2. Create a virtual environment (recommended)

```bash
cd audiostream-pro
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If you don’t use a venv, install with the same Python you’ll use to run the app (e.g. `python3 -m pip install -r requirements.txt`).

First run will download the Demucs model (~300 MB); this is one-time.

### 4. Run the app

**Desktop (PyQt6):**

```bash
python3 app.py
```

**Web (browser):**

```bash
python3 web_app.py
```

This starts a local server (default: http://127.0.0.1:5050) and opens the page in your browser. Use the same workflow: drop or select a video, wait for processing, then download the WAV.

---

## Quality and model options

Before processing you can choose:

- **Model** (Demucs engine):
  - **HTDemucs (default)** — 4 stems (drums, bass, other, vocals). Good balance of speed and quality.
  - **MDX Extra Q** — Bag of 4 models, often higher quality; slower.
  - **HTDemucs 6-stem** — Also separates piano and guitar; useful for richer backing tracks.

- **Quality** (number of “shifts” for equivariant stabilization):
  - **Fast (1 shift)** — Fastest, good for previews.
  - **Balanced (2 shifts)** — Good default.
  - **High (5 shifts)** — Better separation, slower.
  - **Best (10 shifts)** — Best quality, slowest (as in the Demucs paper).

Higher quality and MDX Extra Q use more CPU/GPU time but can improve separation and reduce vocal bleed in the background track.

---

## Usage

1. **Choose model and quality** (optional) — Pick **Model** and **Quality** in the dropdowns (desktop or web).

2. **Select a video**  
   - Drag and drop a video file (`.mp4`, `.mov`, etc.) onto the drop zone, or  
   - Click **Select Video** and choose a file.

3. **Wait for processing**  
   - **Extracting audio from video…** — FFmpeg creates a temporary WAV.  
   - **Running AI separation (Demucs)…** — Selected model produces stems.  
   - **Combining background stems…** — All non-vocal stems are mixed and saved.  
   - Progress bar updates through these steps.

4. **Open output**  
   - When **Done** is shown, click **Open Output Folder**.  
   - Output file: `{video_name}_background_music.wav` in a folder `AudioStem-Pro_output` next to the original video (or in a chosen location if we add that option later).

---

## Project structure

```
AudioStem-Pro/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── app.py                 # Desktop entry (PyQt6)
├── web_app.py             # Web entry (Flask); run to view in browser
├── core/
│   ├── __init__.py
│   ├── audio_utils.py     # FFmpeg check + extract video → WAV
│   ├── pipeline.py        # Shared pipeline (used by desktop + web)
│   └── worker.py          # QThread wrapper for desktop
├── ui/
│   ├── __init__.py
│   └── main_window.py     # Desktop window
├── templates/
│   └── index.html         # Web UI template
└── static/
    ├── css/style.css      # Web styles (dark theme)
    └── js/main.js         # Web: upload, progress polling, download
```

### Logic flow

1. User optionally selects **Model** and **Quality**, then selects or drops a video.
2. **audio_utils**: Extract audio to a temporary WAV (44.1 kHz) via FFmpeg.
3. **pipeline**: Run the chosen Demucs model on that WAV (with the chosen number of shifts).
4. **pipeline**: Sum all stems except vocals and save as `{name}_background_music.wav`.
5. Temporary files are removed; UI shows **Done** and **Open Output Folder** (desktop) or **Download WAV** (web).

---

## Troubleshooting

- **`No module named 'demucs'`** — Dependencies are not installed for the Python you’re using. Install them: `pip install -r requirements.txt` (with your venv activated), or `python3 -m pip install -r requirements.txt`. Then run the app with the same interpreter (e.g. `python3 app.py` or `python3 web_app.py`).

---

## Error handling

- **FFmpeg missing** — Warning dialog at startup with install hints.
- **Video file not found** — Message if the chosen path doesn’t exist.
- **FFmpeg extraction failure** — Error dialog with FFmpeg’s stderr.
- **Demucs failure** — Exception is caught in the worker and emitted as an error message to the UI.

---

## License and credits

- **Author** — [Eduarth Schmidt](https://aiautomationflows.com/)  
- **Demucs** — [facebookresearch/demucs](https://github.com/facebookresearch/demucs) (Meta).  
- **FFmpeg** — [ffmpeg.org](https://ffmpeg.org).  
- **PyQt6** — [Riverbank Computing](https://www.riverbankcomputing.com/software/pyqt/).  
