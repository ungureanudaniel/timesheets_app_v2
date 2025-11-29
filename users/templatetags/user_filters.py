from django import template

register = template.Library()

@register.filter
def filter_by_role(users, role):
    """Filter users by role"""
    return [user for user in users if user.role == role]

@register.filter
def user_role_badge_class(role):
    """Return Bootstrap badge class based on role"""
    role_classes = {
        'ADMIN': 'bg-danger',
        'MANAGER': 'bg-warning', 
        'REPORTER': 'bg-info'
    }
    return role_classes.get(role, 'bg-secondary')

@register.filter
def can_edit_user(current_user, target_user):
    """Check if current user can edit target user"""
    if current_user.is_admin:
        return True
    elif current_user.is_manager and target_user.role != 'ADMIN':
        return True
    return False