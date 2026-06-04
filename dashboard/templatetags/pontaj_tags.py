from django import template
register = template.Library()

@register.filter(name='dictget')
def dictget(dictionary, key):
    if not dictionary:
        return None
    # Safeguard lookup parsing for both integer indices and standard dictionary objects
    return dictionary.get(key) or dictionary.get(str(key))