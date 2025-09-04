from django import template

register = template.Library()

@register.filter(name="split_csv")
def split_csv(value, sep=","):
    """
    Split a CSV string and return a list of stripped, non-empty tokens.
    Usage: {{ my_csv|split_csv:"," }}
    """
    if not value:
        return []
    return [t.strip() for t in str(value).split(sep) if t.strip()]


# Simple no-op filters you can extend later if needed
@register.filter(name="identity")
def identity(value):
    return value