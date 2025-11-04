from pathlib import Path
from datetime import datetime
import os, io
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible

@deconstructible
class CategorizedUploadTo:
    """
    Serializable callable for ImageField.upload_to.
    Keeps (app_label, model, field) so Django can de/reconstruct it in migrations.
    """
    def __init__(self, app_label: str, model: str, field: str):
        self.app_label = app_label
        self.model = model
        self.field = field

    def __call__(self, instance, filename: str):
        user_id = getattr(getattr(instance, "user", None), "pk", "anon")
        today = datetime.utcnow()
        name = Path(filename).name
        return f"{self.app_label}/{self.model}/{self.field}/{user_id}/{today:%Y/%m}/{name}"

# Optional helper so your model code can stay readable:
def categorized_upload_to(app_label: str, model: str, field: str):
    return CategorizedUploadTo(app_label, model, field)


def optimize_image_file(file_field,
                        max_side: int = 1920,
                        jpg_quality: int = 82,
                        webp_quality: int = 82,
                        allow_webp: bool = True):
    if not file_field or not getattr(file_field, "name", None):
        return False

    f = file_field.file
    f.open("rb")
    data = f.read()
    f.close()

    old_size = len(data)
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im)

    w, h = im.size
    if max(w, h) > max_side:
        if w >= h:
            new_w = max_side
            new_h = int(h * (new_w / w))
        else:
            new_h = max_side
            new_w = int(w * (new_h / h))
        im = im.resize((new_w, new_h), Image.LANCZOS)

    ext = Path(file_field.name).suffix.lower()

    def _encode_as(fmt: str):
        buf = io.BytesIO()
        img = im
        if fmt == "JPEG":
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=jpg_quality, optimize=True, progressive=True)
        elif fmt == "PNG":
            img.save(buf, format="PNG", optimize=True)
        elif fmt == "WEBP":
            img.save(buf, format="WEBP", quality=webp_quality, method=6)
        else:
            return None
        return buf.getvalue()

    if ext in (".jpg", ".jpeg"):
        native = _encode_as("JPEG")
    elif ext == ".png":
        native = _encode_as("PNG")
    elif ext == ".webp":
        native = _encode_as("WEBP")
    else:
        native = _encode_as("JPEG")

    best_bytes = native
    best_ext = ext

    if allow_webp:
        webp_bytes = _encode_as("WEBP")
        if webp_bytes and len(webp_bytes) < len(best_bytes):
            best_bytes = webp_bytes
            best_ext = ".webp"

    if len(best_bytes) >= old_size:
        return False

    base_name = Path(file_field.name).name
    tmp = ContentFile(best_bytes)
    file_field.storage.delete(file_field.name)
    file_field.save(base_name, tmp, save=False)
    return True
