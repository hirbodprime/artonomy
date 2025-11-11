# core/utils/validators.py
from django.core.exceptions import ValidationError

def validate_file_size_1mb(file_obj):
    """Reject files larger than 1 MB."""
    max_size = 1 * 1024 * 1024  # 1 MB in bytes
    if file_obj.size > max_size:
        size_in_mb = round(file_obj.size / (1024 * 1024), 2)
        raise ValidationError(
            f"حجم فایل {size_in_mb} مگابایت است. حداکثر حجم مجاز 1 مگابایت می‌باشد."
        )
