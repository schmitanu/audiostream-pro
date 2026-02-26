"""
Shared pipeline: extract audio from video → Demucs separation → combine stems.
Used by both the desktop worker (QThread) and the web app (background thread).
Progress is reported via an optional callback(status: str, progress: int 0-100).
"""

import tempfile
from pathlib import Path
from typing import Callable

from .audio_utils import extract_audio_to_wav

# Demucs model options (bag names from demucs remote repo)
DEMUCS_MODELS = [
    ("htdemucs", "HTDemucs (default, 4 stems)"),
    ("mdx_extra_q", "MDX Extra Q (high quality, 4 stems)"),
    ("htdemucs_6s", "HTDemucs 6-stem (drums, bass, other, vocals, piano, guitar)"),
]

# Quality = number of shifts (equivariant stabilization). More = better quality, slower.
QUALITY_PROFILES = [
    (1, "Fast (1 shift)"),
    (2, "Balanced (2 shifts)"),
    (5, "High (5 shifts)"),
    (10, "Best (10 shifts)"),
]


def run_pipeline(
    video_path: str | Path,
    output_dir: str | Path | None = None,
    progress_callback: Callable[[str, int], None] | None = None,
    *,
    model_name: str = "htdemucs",
    shifts: int = 1,
) -> Path:
    """
    Extract background music (no vocals) from a video file.

    Args:
        video_path: Path to video (.mp4, .mov, etc.).
        output_dir: Directory for output WAV. Default: same folder as video, subdir AudioStem-Pro_output.
        progress_callback: Optional callback(status_message, progress_percent).
        model_name: Demucs model bag name (htdemucs, mdx_extra_q, htdemucs_6s).
        shifts: Number of random shifts for quality (1=fast, 10=best, slower).

    Returns:
        Path to the output WAV file: {video_stem}_background_music.wav

    Raises:
        FileNotFoundError, RuntimeError: On extraction or separation failure.
    """
    video_path = Path(video_path).resolve()
    if output_dir is None:
        output_dir = video_path.parent / "AudioStem-Pro_output"
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    def report(status: str, progress: int):
        if progress_callback:
            progress_callback(status, progress)

    report("Extracting audio from video…", 0)

    with tempfile.TemporaryDirectory(prefix="audiostem_") as tmpdir:
        tmp = Path(tmpdir)
        wav_path = tmp / "extracted.wav"
        extract_audio_to_wav(video_path, wav_path)
        report("Extracting audio from video…", 25)

        report("Running AI separation (Demucs)…", 35)
        import torch
        from demucs.pretrained import get_model
        from demucs.separate import load_track
        from demucs.apply import apply_model
        from demucs.audio import save_audio

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = get_model(model_name)
        model.to(device)
        model.eval()
        wav = load_track(wav_path, model.audio_channels, model.samplerate)
        ref = wav.mean(0)
        wav = wav - ref.mean()
        wav = wav / (ref.std() + 1e-8)
        sources = apply_model(
            model, wav[None], device=device, shifts=shifts, split=True, overlap=0.25,
            progress=False,
        )[0]
        sources = sources * ref.std() + ref.mean()
        report("Running AI separation (Demucs)…", 85)

        report("Combining background stems…", 90)
        # Sum all stems except vocals (works for 4-stem and 6-stem models)
        if "vocals" in model.sources:
            vocals_idx = model.sources.index("vocals")
            background = sum(sources[i] for i in range(len(sources)) if i != vocals_idx)
        else:
            background = sources.sum(dim=0)
        out_name = video_path.stem + "_background_music.wav"
        out_path = output_dir / out_name
        save_audio(
            background,
            str(out_path),
            model.samplerate,
            clip="rescale",
        )

    report("Done", 100)
    return out_path
