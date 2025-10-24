# portfolio/utils/images.py
from pathlib import Path
from datetime import datetime
import os, io, tempfile
from PIL import Image, ImageOps
from django.core.files.base import ContentFile

def categorized_upload_to(app_label: str, model: str, field: str):
    """Factory returning an upload_to callable."""
    def _inner(instance, filename: str):
        user_id = getattr(getattr(instance, "user", None), "pk", "anon")
        today = datetime.utcnow()
        name = Path(filename).name  # keep original name
        return f"{app_label}/{model}/{field}/{user_id}/{today:%Y/%m}/{name}"
    return _inner

def optimize_image_file(file_field,
                        max_side: int = 1920,
                        jpg_quality: int = 82,
                        webp_quality: int = 82,
                        allow_webp: bool = True):
    """
    Read ImageField, auto-rotate (EXIF), resize (keep aspect, max_side),
    strip heavy metadata, and re-encode (JPEG/PNG or WEBP if allowed & smaller).
    Replaces the file IN-PLACE (same name).
    """
    if not file_field or not getattr(file_field, "name", None):
        return False

    # Read bytes
    f = file_field.file
    f.open("rb")
    data = f.read()
    f.close()

    old_size = len(data)
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im)

    # Resize preserving aspect
    w, h = im.size
    if max(w, h) > max_side:
        if w >= h:
            new_w = max_side
            new_h = int(h * (new_w / w))
        else:
            new_h = max_side
            new_w = int(w * (new_h / h))
        im = im.resize((new_w, new_h), Image.LANCZOS)

    # Decide target encoders
    ext = Path(file_field.name).suffix.lower()
    orig_mode = im.mode

    # Prepare candidates: original format vs webp
    def _encode_as(fmt: str):
        buf = io.BytesIO()
        img = im
        if fmt == "JPEG":
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=jpg_quality, optimize=True, progressive=True)
        elif fmt == "PNG":
            # keep alpha; optimize
            img.save(buf, format="PNG", optimize=True)
        elif fmt == "WEBP":
            # auto alpha
            img.save(buf, format="WEBP", quality=webp_quality, method=6)
        else:
            return None
        return buf.getvalue()

    # Encode in native-ish format first
    if ext in (".jpg", ".jpeg"):
        native = _encode_as("JPEG")
    elif ext == ".png":
        native = _encode_as("PNG")
    elif ext == ".webp":
        native = _encode_as("WEBP")
    else:
        # default to JPEG if unsure
        native = _encode_as("JPEG")

    best_bytes = native
    best_ext = ext

    # Try WEBP as alternate if allowed; pick smaller
    if allow_webp:
        webp_bytes = _encode_as("WEBP")
        if webp_bytes and len(webp_bytes) < len(best_bytes):
            best_bytes = webp_bytes
            best_ext = ".webp"

    # If WEBP wins but original path isn’t .webp, keep SAME name (no 404s) but write WEBP bytes.
    # Browsers will still render by sniffing; if you prefer extension-switching, add a renamer.
    if len(best_bytes) >= old_size:
        return False  # not worth replacing

    # Replace content in storage
    base_dir, base_name = os.path.split(file_field.name)
    # Write to temp, then save back with same name to avoid path changes
    tmp = ContentFile(best_bytes)
    file_field.storage.delete(file_field.name)  # remove old
    file_field.save(base_name, tmp, save=False)  # same basename
    return True
    