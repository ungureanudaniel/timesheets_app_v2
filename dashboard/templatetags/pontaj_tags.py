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

@register.filter
def format_minutes(minutes):
    """
    Convert minutes to readable format.
    510 -> 8h 30min
    60 -> 1h
    45 -> 45min
    0 -> 0min
    """
    if not minutes:
        return "0min"
    
    minutes = int(minutes)
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}min"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}min"

@register.filter
def format_minutes_short(minutes):
    """
    Short format: 8:30
    """
    if not minutes:
        return "0"
    
    minutes = int(minutes)
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}:{mins:02d}"

@register.filter
def format_minutes_to_hours(minutes):
    """
    510 -> 8.5
    """
    if not minutes:
        return 0
    return round(minutes / 60, 1)