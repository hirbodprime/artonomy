from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.conf import settings
import os

def _should_save_as_webp(pil_image, original_name: str) -> bool:
    """
    Save as WebP when the original is PNG (or very large) to reduce size.
    WebP keeps alpha; JPEG doesn't.
    """
    name = (original_name or "").lower()
    has_alpha = pil_image.mode in ("RGBA", "LA") or (pil_image.mode == "P" and "transparency" in pil_image.info)
    return name.endswith(".png") or has_alpha

def compress_image_file(django_file,
                        quality: int | None = None,
                        max_size: tuple[int, int] | None = None):
    """
    Compress an uploaded ImageField file.
    - Resizes down to max_size (keep aspect) if set
    - Chooses WEBP for PNG/alpha, JPEG otherwise
    - Returns ContentFile ready to assign back to ImageField
    """
    quality = quality or getattr(settings, "IMAGE_DEFAULT_QUALITY", 72)
    max_size = max_size or getattr(settings, "IMAGE_MAX_SIZE", (2560, 2560))

    # Open with Pillow
    im = Image.open(django_file)

    # Ensure an 8-bit/channel mode for consistent saving
    if im.mode in ("P", "RGBA", "LA"):
        # Convert palette/alpha images to RGBA to preserve alpha for WEBP
        im = im.convert("RGBA")
    elif im.mode not in ("RGB", "L"):
        im = im.convert("RGB")

    # Downscale if too large (keeps aspect)
    im.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Choose format
    save_as_webp = _should_save_as_webp(im, getattr(django_file, "name", ""))
    out_format = "WEBP" if save_as_webp else "JPEG"

    # If saving JPEG, drop alpha
    if out_format == "JPEG" and im.mode in ("RGBA", "LA"):
        im = im.convert("RGB")

    # Encode
    buf = BytesIO()
    # optimize=True makes Pillow spend more time to shrink better
    save_kwargs = dict(quality=quality, optimize=True)
    if out_format == "WEBP":
        # lossless=False keeps size down; you can flip to True for lossless PNG-like
        save_kwargs.update(method=6)  # better compression
    im.save(buf, format=out_format, **save_kwargs)

    # Pick a good output name
    base, _ext = os.path.splitext(getattr(django_file, "name", "upload"))
    ext = ".webp" if out_format == "WEBP" else ".jpg"
    new_name = f"{base}_compressed{ext}"

    return ContentFile(buf.getvalue(), name=new_name)
