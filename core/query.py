# core/query.py
def _common_selects(qs):
    return (
        qs.select_related("author")
          .prefetch_related("images", "videos", "categories", "chapters")
    )
