# import os
# import subprocess
# from django.conf import settings

# def ffmpeg_bin():
#     return getattr(settings, "FFMPEG_BIN", "ffmpeg")

# def compress_video_inplace(input_path: str,
#                            crf: int = 28,
#                            preset: str = "fast") -> str:
#     """
#     Compress a video file with ffmpeg.
#     Returns the path to the new compressed file.
#     """
#     assert os.path.exists(input_path), f"Input not found: {input_path}"
#     base, ext = os.path.splitext(input_path)
#     out_path = f"{base}_compressed.mp4"

#     # If already compressed once, don't do it again
#     if input_path.endswith("_compressed.mp4"):
#         return input_path

#     cmd = [
#         ffmpeg_bin(), "-y",
#         "-i", input_path,
#         "-vcodec", "libx264", "-crf", str(crf), "-preset", preset,
#         "-acodec", "aac", "-movflags", "+faststart",
#         out_path
#     ]
#     subprocess.run(cmd, check=True)
#     return out_path
import os
import subprocess
from django.conf import settings
from tempfile import NamedTemporaryFile

def ffmpeg_bin():
    return getattr(settings, "FFMPEG_BIN", "ffmpeg")

def compress_video_inplace(input_path: str, crf: int = 28, preset: str = "fast") -> str:
    """
    Re-encode `input_path` to H.264/AAC using CRF and replace the original file atomically.
    Returns the final (original) path.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input not found: {input_path}")

    # Don't double-compress files already marked as compressed
    if input_path.endswith("_compressed.mp4"):
        return input_path

    # Write to a temp file in the same directory to allow atomic replace
    dir_name = os.path.dirname(input_path)
    with NamedTemporaryFile(prefix="tmp_compress_", suffix=".mp4", dir=dir_name, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            ffmpeg_bin(), "-y",
            "-i", input_path,
            # ensure even dimensions to avoid encoder errors
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-vcodec", "libx264", "-crf", str(crf), "-preset", preset,
            "-acodec", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            tmp_path,
        ]
        subprocess.run(cmd, check=True)

        # On success, atomically replace original
        os.replace(tmp_path, input_path)
        return input_path
    except Exception:
        # Clean up temp file if something goes wrong
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        finally:
            raise
