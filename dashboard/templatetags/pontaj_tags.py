from django import template

register = template.Library()

@register.filter(name='dictget')
def dictget(dictionary, key):
    # If it's a dictionary, look up by key normally
    if isinstance(dictionary, dict):
        return dictionary.get(key) or dictionary.get(str(key))
    
    # Defensive Fallback: If it's a list/matrix array, handle lookup by index offset safely
    elif isinstance(dictionary, list):
        try:
            idx = int(key) - 1 # Days are 1-indexed, lists are 0-indexed
            if 0 <= idx < len(dictionary):
                return dictionary[idx]
        except (ValueError, TypeError):
            pass
            
    return None