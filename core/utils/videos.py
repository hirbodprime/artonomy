import os
import subprocess
from django.core.files.storage import default_storage

def compress_video_field(instance, field_name, max_width=1280, video_bitrate="1500k"):
    """
    ویدیو فیلد مشخص‌شده را با استفاده از ffmpeg فشرده می‌کند.
    - max_width: حداکثر عرض ویدیو (مثلاً 1280)
    - video_bitrate: بیت‌ریت ویدیو (مثلاً 1500k)

    ⚠️ نیاز به نصب ffmpeg روی سرور دارد.
    """
    field = getattr(instance, field_name, None)
    if not field:
        return

    try:
        path = field.path
    except (ValueError, AttributeError):
        # فایل هنوز ذخیره نشده یا مسیری ندارد
        return

    if not default_storage.exists(field.name):
        return

    root, ext = os.path.splitext(path)
    temp_path = root + ".tmp" + ext

    # دستور ffmpeg ساده برای فشرده‌سازی
    cmd = [
        "ffmpeg",
        "-y",
        "-i", path,
        "-vf", f"scale='min({max_width},iw)':-2",
        "-b:v", video_bitrate,
        "-c:v", "libx264",
        "-preset", "slow",
        "-c:a", "aac",
        "-movflags", "+faststart",
        temp_path,
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # جایگزین کردن فایل اصلی با نسخه‌ی فشرده
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        # اگر فشرده‌سازی شکست خورد، فایل اصلی را دست‌نخورده می‌گذاریم
        return
