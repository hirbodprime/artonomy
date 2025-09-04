from django import template

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css):
    """
    Add CSS class to a Django BoundField's widget at render time.
    If 'field' is not a BoundField (e.g., a plain string), just return it unchanged.
    """
    # If it's already a rendered string or not a BoundField, bail out gracefully
    if not hasattr(field, "field") or not hasattr(field.field, "widget"):
        return field

    attrs = field.field.widget.attrs.copy()
    existing = attrs.get("class", "")
    attrs["class"] = (existing + " " + css).strip()
    return field.as_widget(attrs=attrs)


