import os
import subprocess
from django.conf import settings

def ffmpeg_bin():
    return getattr(settings, "FFMPEG_BIN", "ffmpeg")

def compress_video_inplace(input_path: str,
                           crf: int = 28,
                           preset: str = "fast") -> str:
    """
    Compress a video file with ffmpeg.
    Returns the path to the new compressed file.
    """
    assert os.path.exists(input_path), f"Input not found: {input_path}"
    base, ext = os.path.splitext(input_path)
    out_path = f"{base}_compressed.mp4"

    # If already compressed once, don't do it again
    if input_path.endswith("_compressed.mp4"):
        return input_path

    cmd = [
        ffmpeg_bin(), "-y",
        "-i", input_path,
        "-vcodec", "libx264", "-crf", str(crf), "-preset", preset,
        "-acodec", "aac", "-movflags", "+faststart",
        out_path
    ]
    subprocess.run(cmd, check=True)
    return out_path
