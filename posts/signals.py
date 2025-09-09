import os
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PostVideo, Post
from .video_utils import compress_video_inplace

@receiver(post_save, sender=PostVideo)
def compress_postvideo_file(sender, instance: PostVideo, created, **kwargs):
    """
    Compress video after the PostVideo record is saved (first time).
    """
    if not getattr(settings, "VIDEO_COMPRESS", True):
        return
    if not instance.file:
        return
    path = instance.file.path
    if not os.path.exists(path):
        return

    # Skip if already compressed
    if path.endswith("_compressed.mp4"):
        return

    try:
        out_path = compress_video_inplace(path, crf=28, preset="fast")
    except Exception:
        # Silent fail to not crash user flows; optionally log
        return

    # Point the FileField to the new file
    rel = os.path.relpath(out_path, settings.MEDIA_ROOT)
    instance.file.name = rel
    instance.save(update_fields=["file"])


@receiver(post_save, sender=Post)
def compress_post_video_field(sender, instance: Post, created, **kwargs):
    """
    If Post.video (the single-file shortcut) is used, compress that too.
    """
    if not getattr(settings, "VIDEO_COMPRESS", True):
        return
    if not instance.video:
        return

    path = instance.video.path
    if not os.path.exists(path) or path.endswith("_compressed.mp4"):
        return

    try:
        out_path = compress_video_inplace(path, crf=28, preset="fast")
    except Exception:
        return

    rel = os.path.relpath(out_path, settings.MEDIA_ROOT)
    instance.video.name = rel
    instance.save(update_fields=["video"])
