# core/utils/images.py
import os
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image

def compress_image_field(instance, field_name, max_width=1600, quality=75):
    """
    تصویر فیلد مشخص‌شده را کوچک و فشرده می‌کند
    و دوباره روی همان فیلد می‌نویسد (بدون ساختن مسیر تودرتو).
    """
    field = getattr(instance, field_name, None)
    if not field:
        return

    # اگر هیچ فایلی روی فیلد نیست
    if not getattr(field, "name", None):
        return

    try:
        img = Image.open(field)
    except Exception:
        # اگر فایل تصویر نباشد، بی‌خیال فشرده‌سازی شو
        return

    # تبدیل به RGB (برای JPEG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # تغییر سایز اگر عرض از max_width بیشتر بود
    if max_width and img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    # ذخیره در حافظه
    buffer = BytesIO()
    img.save(buffer, format="JPEG", optimize=True, quality=quality)
    buffer.seek(0)
    file_content = ContentFile(buffer.read())

    # 🔴 نکته مهم: فقط اسم فایل، نه کل مسیر
    original_name = os.path.basename(field.name)  # "file.jpg" از "artists/categories/1/file.jpg"

    # اینجا دوباره upload_to روی original_name اعمال می‌شود و مسیر درست ساخته می‌شود
    field.save(original_name, file_content, save=False)
