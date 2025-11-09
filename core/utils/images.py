# core/utils/images.py
import io
from PIL import Image
from django.core.files.base import ContentFile


def compress_image_field(instance, field_name: str, max_width: int = 1600, quality: int = 70):
    """
    Opens instance.<field_name>, resizes if too wide, and re-saves as JPEG
    with given quality. Uses save=False so caller can call super().save().
    """
    field = getattr(instance, field_name, None)
    if not field:
        return

    try:
        img = Image.open(field)
    except Exception:
        return  # not an image or something went wrong

    # Skip GIF / animated images (optional)
    if img.format == "GIF":
        return

    # Drop alpha for JPEG
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    w, h = img.size
    if w > max_width:
        new_h = int(max_width * h / w)
        img = img.resize((max_width, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    # Strong compression: lower quality → smaller file
    img.save(buf, format="JPEG", optimize=True, quality=quality)
    buf.seek(0)

    file_content = ContentFile(buf.read())
    # reuse same name (storage will overwrite)
    field.save(field.name, file_content, save=False)
