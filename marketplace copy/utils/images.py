from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys, os

def compress_image(uploaded_file, *, max_side=2000, webp=True, quality=82, strip_exif=True):
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)  # fix orientation

    # convert to RGB
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # resize with aspect ratio
    img.thumbnail((max_side, max_side), Image.LANCZOS)

    buf = BytesIO()
    fmt = "WEBP" if webp else "JPEG"
    save_kwargs = {"quality": quality, "optimize": True}
    if fmt == "WEBP":
        save_kwargs.update({"method": 6})

    if strip_exif and "exif" in img.info:
        # do nothing; saving to new buffer without exif strips metadata
        pass

    img.save(buf, fmt, **save_kwargs)
    buf.seek(0)

    # build InMemoryUploadedFile for Django field
    base, _ = os.path.splitext(uploaded_file.name)
    ext = ".webp" if webp else ".jpg"
    new_name = f"{base}{ext}"

    return InMemoryUploadedFile(
        buf,               # file
        None,              # field_name (filled by form/model)
        new_name,
        f"image/{'webp' if webp else 'jpeg'}",
        buf.getbuffer().nbytes,
        None
    )
